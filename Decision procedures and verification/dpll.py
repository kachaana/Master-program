import argparse
import time

import formula2cnf

class DPLL:
    def __init__(self):
        self.clauses = []
        self.made_decisions = 0
        self.made_propagations = 0
        self.assignment = set()

    def reinit(self):
        self.clauses = []
        self.made_decisions = 0
        self.made_propagations = 0
        self.assignment = set()

    # Formula in DIMACS format to solve.
    def solve(self, formula) -> bool:
        # Clear class members.
        self.reinit()
        # Read clauses.
        self.read_clauses(formula)
        # Run DPLL algorithm.
        return self.dpll(self.clauses, self.assignment)

    # Method chooses the literal, that should be decided.
    # This will find the literal, that occurs the most in clauses depending on the sign.
    # If there are more candidates:
    #   1. The same number of occurrences for different keys - the key with the less value will be chosen.
    #   2. The same number of positive and negative occurrences for one key - positive literal will be chosen.
    def choose_literal(self, formula) -> int:
        positive_clause_cnt = dict()
        negative_clause_cnt = dict()

        for clause in formula:
            for literal in clause:
                if literal > 0:
                    if literal not in positive_clause_cnt:
                        positive_clause_cnt[literal] = 1
                    else:
                        positive_clause_cnt[literal] += 1
                else:
                    if abs(literal) not in negative_clause_cnt:
                        negative_clause_cnt[abs(literal)] = 1
                    else:
                        negative_clause_cnt[abs(literal)] += 1

        max_pos = -1
        max_neg = -1
        if len(positive_clause_cnt) > 0:
            max_pos = max(positive_clause_cnt, key=lambda k: (positive_clause_cnt[k], -k))
        if len(negative_clause_cnt) > 0:
            max_neg = max(negative_clause_cnt, key=lambda k: (negative_clause_cnt[k], -k))

        if max_neg == -1 and max_pos == -1:
            raise Exception

        if max_neg == -1:
            return max_pos
        elif max_pos == -1:
            return -max_neg

        if positive_clause_cnt[max_pos] > negative_clause_cnt[max_neg]:
            return max_pos
        elif positive_clause_cnt[max_pos] < negative_clause_cnt[max_neg]:
            return -max_neg
        else:
            if max_pos >= max_neg:
                return max_pos
            return -max_neg

    # This will eliminate formula by provided assignment.
    # Satisfied clause or literal with opposite sign will be removed.
    def eliminate_formula(self, formula, assignment: set):
        reduced_formula = []
        for clause in formula:
            new_clause = []
            ignore = False
            for literal in clause:
                if literal in assignment:
                    ignore = True
                    break
                elif -literal in assignment:
                    continue
                else:
                    new_clause.append(literal)
            if ignore is False:
                reduced_formula.append(new_clause)
        return reduced_formula

    def unit_propagation(self, formula, assignment: set) -> (bool, list):

        reduced_formula = self.eliminate_formula(formula, assignment)

        # Unit clauses
        unit_clauses = set([clause[0] for clause in reduced_formula if len(clause) == 1])

        while len(unit_clauses) > 0 and len(reduced_formula) > 0:
            self.made_propagations += 1

            literal = unit_clauses.pop()
            assignment.add(literal)

            reduced_formula_tmp = []

            for clause in reduced_formula:
                # Clause is satisfied, so it will be removed from formula.
                if literal in clause:
                    continue
                # If a clause has the literal but with opposite sign, the literal will be removed from clause.
                new_clause = [other_literal for other_literal in clause if other_literal != -literal]

                # The whole formula is unsatisfied if there are unit clauses with the same literal,
                # but different signs.
                # Return UNSAT.
                if not new_clause:
                    return False, []
                # New unit clause.
                if len(new_clause) == 1:
                    unit_clauses.add(new_clause[0])
                reduced_formula_tmp.append(new_clause)
            reduced_formula = reduced_formula_tmp
        return True, reduced_formula

    def dpll(self, formula, assignment : set):
        result, reduced_formula = self.unit_propagation(formula, assignment)

        if len(reduced_formula) == 0 and result is True:
            self.assignment = sorted(assignment, key=abs)
            return True

        if result is False:
            return False

        decided_literal = self.choose_literal(reduced_formula)
        self.made_decisions += 1

        new_assignment = assignment.copy()
        new_assignment.add(decided_literal)
        if self.dpll(reduced_formula, new_assignment):
            return True

        new_assignment = assignment.copy()
        new_assignment.add(-decided_literal)
        if self.dpll(reduced_formula, new_assignment):
            return True

        return False

    # Parse method, that reads clauses from DIMASC format file
    # and store them to self.clauses.
    def read_clauses(self, formula):
        for line in formula.splitlines():
            # Comments are not interesting.
            if len(line) == 0 or line[0] == 'c':
                continue

            parts = line.split()

            # Rows with clauses.
            if line[0] != 'p':
                # Remove zero.
                parts = parts[:-1]
                self.clauses.append([int(item) for item in parts])
    def print_info(self):
        print("Sufficient model =", self.assignment)
        print("Sufficient model size = ", len(self.assignment))
        print()
        print("Number of decisions =", self.made_decisions)
        print("Number of propagations =", self.made_propagations)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=None, type=str, help="Input file with formula in NNF SMT-LIB format "
                                                                "or DIMACS CNF format.")
    args = parser.parse_args()

    if args.input is None:
        print("Provide a file with formula.")
        exit(1)

    formula = ""
    # Translate SMT-LIB to DIMACS format
    if args.input.endswith('.sat'):
        with open(args.input, 'r') as file:
            formula = file.readline()
        # It is better to use left-to-right mode as the resulting formula will have fewer clauses :)
        translator = formula2cnf.Formula2CNF(mode='left_to_right')
        formula = translator.run(formula)
    # Just read DIMACS format
    elif args.input.endswith('.cnf'):
        with open(args.input, 'r') as file:
            formula = file.readline()

    dpll = DPLL()

    start = time.time()
    result = dpll.solve(formula)
    end = time.time()

    if result is True:
        print("SAT")
        print()
        print("CPU time =", end - start)
        print()
        dpll.print_info()

    else:
        print("UNSAT")

