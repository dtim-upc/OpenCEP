from datetime import timedelta
from base.Pattern import Pattern
from base.transformation.RuleTransformationParameters import RuleTransformationParameters
from condition.CompositeCondition import AndCondition
from condition.Condition import TrueCondition, BinaryCondition, Variable
from base.PatternStructure import AndOperator, SeqOperator, PrimitiveEventStructure, NegationOperator, OrOperator

from base.transformation.RuleTransformationTypes import RuleTransformationTypes
from base.transformation.PatternTransformation import PatternTransformation


def ruleTransformationTests():
    andAndPatternTransformationTest()
    innerOrPatternTransformationTest()
    notAndPatternTransformationTest()
    notOrPatternTransformationTest()
    topmostOrPatternTransformationTest()
    notNotPatternTransformationTest()
    print("Rule Transformation unit tests executed successfully.")


def andAndPatternTransformationTest():
    pattern = Pattern(
        AndOperator(PrimitiveEventStructure("AAPL", "a"),
                    NegationOperator(PrimitiveEventStructure("AMZN", "z")),
                    PrimitiveEventStructure("GOOG", "g"),
                    AndOperator(
                        PrimitiveEventStructure("AMZN", "zz"),
                        NegationOperator(PrimitiveEventStructure("GOOG", "gg")),
                        AndOperator(
                            PrimitiveEventStructure("AMZN", "zzz"),
                            NegationOperator(PrimitiveEventStructure("GOOG", "ggg"))
                        )
                    )
                    ),
        TrueCondition(),
        timedelta(minutes=5)
    )
    expected_pattern = Pattern(
        AndOperator(PrimitiveEventStructure("AAPL", "a"),
                    NegationOperator(PrimitiveEventStructure("AMZN", "z")),
                    PrimitiveEventStructure("GOOG", "g"),
                    PrimitiveEventStructure("AMZN", "zz"),
                    NegationOperator(PrimitiveEventStructure("GOOG", "gg")),
                    PrimitiveEventStructure("AMZN", "zzz"),
                    NegationOperator(PrimitiveEventStructure("GOOG", "ggg"))
                    ),
        TrueCondition(),
        timedelta(minutes=5)
    )
    pattern_transformation = PatternTransformation([pattern])
    transformed_patterns = pattern_transformation.transform_patterns()
    print()
    print("Original Pattern:\t\t", pattern.full_structure)
    print("Expected Pattern:\t\t", expected_pattern.full_structure)
    print("Transformed Pattern:\t", transformed_patterns[0].full_structure)

    assert len(transformed_patterns) == 1, "Test andAndPatternTransformation Failed"
    assert expected_pattern.full_structure == transformed_patterns[0].full_structure, \
        "Test andAndPatternTransformation Failed"


def innerOrPatternTransformationTest():
    pattern = Pattern(
        SeqOperator(NegationOperator(PrimitiveEventStructure("AMZN", "z")),
                    OrOperator(PrimitiveEventStructure("GOOG", "g"), PrimitiveEventStructure("AAPL", "a")),
                    OrOperator(PrimitiveEventStructure("GOOG", "gg"), PrimitiveEventStructure("AAPL", "aa"))),
        TrueCondition(),
        timedelta(minutes=5)
    )
    pattern_list = [
        Pattern(
            SeqOperator(NegationOperator(PrimitiveEventStructure("AMZN", "z")),
                        PrimitiveEventStructure("GOOG", "g"),
                        PrimitiveEventStructure("GOOG", "gg")),
            TrueCondition(),
            timedelta(minutes=5)
        ),
        Pattern(
            SeqOperator(NegationOperator(PrimitiveEventStructure("AMZN", "z")),
                        PrimitiveEventStructure("AAPL", "a"),
                        PrimitiveEventStructure("AAPL", "gg")),
            TrueCondition(),
            timedelta(minutes=5)
        ),
        Pattern(
            SeqOperator(NegationOperator(PrimitiveEventStructure("AMZN", "z")),
                        PrimitiveEventStructure("GOOG", "g"),
                        PrimitiveEventStructure("AAPL", "aa")),
            TrueCondition(),
            timedelta(minutes=5)
        ),
        Pattern(
            SeqOperator(NegationOperator(PrimitiveEventStructure("AMZN", "z")),
                        PrimitiveEventStructure("AAPL", "a"),
                        PrimitiveEventStructure("AAPL", "aa")),
            TrueCondition(),
            timedelta(minutes=5)
        )
    ]
    pattern_transformation = PatternTransformation([pattern])
    transformed_patterns = pattern_transformation.transform_patterns()
    print()
    print("Original Pattern:\t\t", pattern.full_structure)
    print("Expected Pattern:\t\t")
    i = 1
    expected_patterns_structures = []
    for tmp_pattern in pattern_list:
        print("\t\t\t\t\t\t", i, " ", tmp_pattern.full_structure)
        i = i + 1
        expected_patterns_structures.append(tmp_pattern.full_structure)
    assert len(transformed_patterns) == len(pattern_list), "Test innerOrPatternTransformation Failed"
    print("Transformed Patterns:\t")
    i = 1
    for tmp_pattern in transformed_patterns:
        print("\t\t\t\t\t\t", i, " ", tmp_pattern.full_structure)
        assert tmp_pattern.full_structure in expected_patterns_structures, "Test innerOrPatternTransformation Failed"
        i = i + 1


def notAndPatternTransformationTest():
    pattern = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"),
                    NegationOperator(AndOperator(
                        PrimitiveEventStructure("AMZN", "z"),
                        PrimitiveEventStructure("GOOG", "g"))),
                    PrimitiveEventStructure("MSFT", "m")
                    ),
        TrueCondition(),
        timedelta(minutes=5)
    )
    expected_pattern = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"),
                    OrOperator(
                        NegationOperator(PrimitiveEventStructure("AMZN", "z")),
                        NegationOperator(PrimitiveEventStructure("GOOG", "g"))),
                    PrimitiveEventStructure("MSFT", "m")),
        TrueCondition(),
        timedelta(minutes=5)
    )

    rules_directive = [RuleTransformationTypes.NOT_AND_PATTERN]
    params = RuleTransformationParameters()
    params.rules_directive = rules_directive
    pattern_transformation = PatternTransformation([pattern], params)
    transformed_patterns = pattern_transformation.transform_patterns()

    print()
    print("Original Pattern:\t\t", pattern.full_structure)
    print("Expected Pattern:\t\t", expected_pattern.full_structure)
    print("Transformed Pattern:\t", transformed_patterns[0].full_structure)

    assert len(transformed_patterns) == 1, "Test notAndPatternTransformation Failed"
    assert transformed_patterns[0].full_structure == expected_pattern.full_structure, \
        "Test notAndPatternTransformation Failed"


def notOrPatternTransformationTest():
    pattern = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"),
                    NegationOperator(OrOperator(
                        PrimitiveEventStructure("AMZN", "z"),
                        PrimitiveEventStructure("GOOG", "g"))),
                    PrimitiveEventStructure("MSFT", "m")
                    ),
        TrueCondition(),
        timedelta(minutes=5)
    )
    expected_pattern = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"),
                    AndOperator(
                        NegationOperator(PrimitiveEventStructure("AMZN", "z")),
                        NegationOperator(PrimitiveEventStructure("GOOG", "g"))),
                    PrimitiveEventStructure("MSFT", "m")),
        TrueCondition(),
        timedelta(minutes=5)
    )

    rules_directive = [RuleTransformationTypes.NOT_OR_PATTERN]
    params = RuleTransformationParameters()
    params.rules_directive = rules_directive
    pattern_transformation = PatternTransformation([pattern], params)
    transformed_patterns = pattern_transformation.transform_patterns()

    print()
    print("Original Pattern:\t\t", pattern.full_structure)
    print("Expected Pattern:\t\t", expected_pattern.full_structure)
    print("Transformed Pattern:\t", transformed_patterns[0].full_structure)

    assert len(transformed_patterns) == 1, "Test notOrPatternTransformation Failed"
    assert transformed_patterns[0].full_structure == expected_pattern.full_structure, \
        "Test notOrPatternTransformation Failed"


def topmostOrPatternTransformationTest():
    pattern = Pattern(
        SeqOperator(PrimitiveEventStructure("AAPL", "a"),
                    OrOperator(
                        PrimitiveEventStructure("AMZN", "z"),
                        PrimitiveEventStructure("GOOG", "g")),
                    PrimitiveEventStructure("MSFT", "m")
                    ),
        TrueCondition(),
        timedelta(minutes=5)
    )
    expected_pattern = Pattern(
        OrOperator(SeqOperator(PrimitiveEventStructure("AAPL", "a"),
                               PrimitiveEventStructure("AMZN", "z"),
                               PrimitiveEventStructure("MSFT", "m")),
                   SeqOperator(PrimitiveEventStructure("AAPL", "a"),
                               PrimitiveEventStructure("GOOG", "g"),
                               PrimitiveEventStructure("MSFT", "m"))
                   ),
        TrueCondition(),
        timedelta(minutes=5)
    )

    rules_directive = [RuleTransformationTypes.TOPMOST_OR_PATTERN]
    params = RuleTransformationParameters()
    params.rules_directive = rules_directive
    pattern_transformation = PatternTransformation([pattern], params)
    transformed_patterns = pattern_transformation.transform_patterns()

    print()
    print("Original Pattern:\t\t", pattern.full_structure)
    print("Expected Pattern:\t\t", expected_pattern.full_structure)
    print("Transformed Pattern:\t", transformed_patterns[0].full_structure)

    assert len(transformed_patterns) == 1, "Test topmostOrPatternTransformation Failed"
    assert transformed_patterns[0].full_structure == expected_pattern.full_structure, \
        "Test topmostOrPatternTransformation Failed"


def notNotPatternTransformationTest():
    pattern = Pattern(
        SeqOperator(PrimitiveEventStructure("AMZN", "z"),
                    NegationOperator(NegationOperator(PrimitiveEventStructure("GOOG", "g")))),
        TrueCondition(),
        timedelta(minutes=5)
    )
    expected_pattern = Pattern(
        SeqOperator(PrimitiveEventStructure("AMZN", "z"),
                    PrimitiveEventStructure("GOOG", "g")),
        TrueCondition(),
        timedelta(minutes=5)
    )

    pattern_transformation = PatternTransformation([pattern])
    transformed_patterns = pattern_transformation.transform_patterns()

    print()
    print("Original Pattern:\t\t", pattern.full_structure)
    print("Expected Pattern:\t\t", expected_pattern.full_structure)
    print("Transformed Pattern:\t", transformed_patterns[0].full_structure)

    assert len(transformed_patterns) == 1, "Test notNotPatternTransformation Failed"
    assert transformed_patterns[0].full_structure == expected_pattern.full_structure, \
        "Test notNotPatternTransformation Failed"

