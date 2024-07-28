import argparse
import sys
import re


class Formula2CNF:
    def __init__(self, mode='eq'):

        # Encoding mode "Equivalences" or "Left-to-right"
        self.mode = mode

        # Original variables ( without negation ).
        # Key = integer, value = original variable name (str).
        self.variables = dict()

        # Original variables ( without negation ).
        # Key = original variable name (str), value = integer.
        self.variables_to_integer = dict()

        # Overall variables count including subformulas substitutions.
        self.variables_cnt = 1

        # Substituted subformulas.
        # Key = integer, value = subformula.
        self.subformulas = dict()

        # All clauses.
        self.clauses = []

        # Root node (variable integer).
        self.root = None

    def reinit(self):
        self.variables = dict()
        self.variables_to_integer = dict()
        self.variables_cnt = 1
        self.subformulas = dict()
        self.clauses = []
        self.root = None

    # Return True if stack variable is an operator, False otherwise.
    def is_operator(self, op_theory) -> bool:
        return op_theory == 'or' or op_theory == 'and' or op_theory == 'not'

    # If var is an original variable - return its integer value;
    # Otherwise do nothing.
    #
    # Note: in case original variables are integers it's still OK to use this method,
    # because stack treats split items as strings, not as integers.
    def get_variable_number(self, var):

        if isinstance(var, int) and (abs(var) in self.subformulas or abs(var) in self.variables):
            return var

        return self.variables_to_integer[var]

    # This method will do following steps:
    #   1. Add needed spaces before and after each bracket.
    #   2. Go through split formula and assign integers to original variables and substitutions (subformulas).
    #
    #   Return: returned value is an integer name of main formula, that left on stack in the end.
    def parse_formula(self, formula):

        # Add spaces before and after brackets
        pattern = r'(?<!\s)([\(\)\[\]\{\}])|([\(\)\[\]\{\}])(?!\s)'
        formula = re.sub(pattern, r' \1\2 ', formula)

        tokens = formula.split()

        stack = []
        for token in tokens:
            if token == '(':
                stack.append(token)
            elif token == ')':
                temp = []
                while stack and stack[-1] != '(':
                    temp.append(stack.pop())
                stack.pop()

                # We want to reverse because of stack LIFO principle.
                temp.reverse()

                # Negative variable is treated as a simple variable, not as subformula.
                # We will just replace "(nox x)" with "-1" on the stack.
                if temp[0] == 'not':
                    var_integer = self.get_variable_number(temp[1])
                    stack.append(-var_integer)
                    continue

                # Replace given variables with its integer if it's possible.
                for i in range(len(temp)):
                    if not self.is_operator(temp[i]):
                        temp[i] = self.get_variable_number(temp[i])

                # Add fresh variables
                stack.append(self.variables_cnt)
                self.subformulas[self.variables_cnt] = temp
                self.variables_cnt += 1
            else:
                stack.append(token)
                # Rules:
                # 1. We don't want to register operators.
                # 2. We don't want to register the same variable twice.
                if not self.is_operator(token) and token not in self.variables_to_integer:
                    self.variables[self.variables_cnt] = token
                    self.variables_to_integer[token] = self.variables_cnt
                    self.variables_cnt += 1

        # root variable
        return stack[0]

    def tseitin_transform(self, root):

        # We are interested only in subformulas (inner nodes),
        # not on variables (lists).

        op = None
        subformula = None

        if root in self.subformulas:
            subformula = self.subformulas[root]
            # Operator is always first due to prefix notation.
            op = subformula[0]

        # "and" or "or"
        if op == "and":
            left_operand = subformula[1]
            right_operand = subformula[2]

            if self.mode == 'eq':
                self.clauses.append([-left_operand, -right_operand, root, 0])
                self.clauses.append([left_operand, -root, 0])
                self.clauses.append([right_operand, -root, 0])

            elif self.mode == 'left_to_right':
                self.clauses.append([-root, left_operand, 0])
                self.clauses.append([-root, right_operand, 0])

            self.tseitin_transform(left_operand)
            self.tseitin_transform(right_operand)

        elif op == "or":
            left_operand = subformula[1]
            right_operand = subformula[2]

            if self.mode == 'eq':
                self.clauses.append([left_operand, right_operand, -root, 0])
                self.clauses.append([-left_operand, root, 0])
                self.clauses.append([-right_operand, root, 0])
            elif self.mode == 'left_to_right':
                self.clauses.append([-root, left_operand, right_operand, 0])

            self.tseitin_transform(left_operand)
            self.tseitin_transform(right_operand)
        else:
            pass

    # Return output as a string.
    def get_output(self) -> str:
        output_text = ""
        output_text += "c \n"
        output_text += "c Substitutions:\n"

        for i in range(1, self.variables_cnt):
            if i in self.variables:
                output_text += "c\t" + str(i) + " = " + self.variables[i] + "\n"
            elif i in self.subformulas:
                output_text += "c\t" + str(i) + " = " + str(self.subformulas[i]) + "\n"
            else:
                raise Exception

        output_text += "c \n"
        output_text += "c Root node is " + str(self.root) + "\n"

        output_text += "c \n"
        output_text += "p cnf " + str(self.variables_cnt - 1) + " " + str(len(self.clauses)) + "\n"

        for clause in self.clauses:
            row = ""
            for var in clause:
                row += str(var) + " "
            row += "\n"
            output_text += row

        print(output_text)
        return ""

    # Reinit all class members.
    # Parse formula and perform tseiting encoding depending on the mode.
    # Returned string is an output to be printed/written to file.
    def run(self, formula) -> str:
        self.reinit()
        self.root = self.parse_formula(formula)
        # Add main clause to all clauses.
        self.clauses.append([self.root, 0])
        self.tseitin_transform(self.root)
        return self.get_output()


if __name__ == '__main__':
    arguments = sys.argv

    input_file = None
    output_file = None

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None, type=str, help="Input file with NNF formula")
    parser.add_argument("--output", default=None, type=str, help="Output file with DIMACS CNF formula.")
    parser.add_argument("--mode", default='eq', choices=['eq', 'left_to_right'], help="Tseitin encoding with left-to-right implications or equivalences.")
    args = parser.parse_args()

    formula = ""
    if args.input is None:
        formula = input()
    else:
        with open(args.input, 'r') as file:
            formula = file.readline()

    translator = Formula2CNF(args.mode)
    output = translator.run(formula)

    if args.output is None:
        print(output)
    else:
        with open(args.input, 'w') as file:
            file.write(output)
