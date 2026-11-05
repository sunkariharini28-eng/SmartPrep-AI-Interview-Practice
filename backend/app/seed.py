"""Sample data: categories, demo users, aptitude questions and coding problems. Idempotent."""
from .database import Category, Question, SessionLocal, User
from .security import hash_password

INTERVIEW_CATEGORIES = [
    "Python", "Java", "C and C++", "JavaScript", "HTML and CSS", "React.js", "Node.js", "SQL and DBMS",
    "Operating Systems", "Computer Networks", "Data Structures and Algorithms", "Machine Learning",
    "Artificial Intelligence", "HR Interview", "Communication Skills",
]

# (section, difficulty, text, options, answer_index, explanation)
APTITUDE = [
    ("Quantitative", "easy", "A train 120 m long passes a pole in 6 seconds. What is its speed in km/h?",
     ["60", "72", "80", "90"], 1, "Speed = 120/6 = 20 m/s. Multiply by 18/5 to get km/h: 20 x 3.6 = 72 km/h."),
    ("Quantitative", "easy", "What is 15% of 240?", ["32", "36", "40", "42"], 1, "0.15 x 240 = 36."),
    ("Quantitative", "medium", "The ratio of two numbers is 3:5 and their sum is 96. Find the larger number.",
     ["36", "48", "60", "72"], 2, "Parts = 8, each part = 12. Larger = 5 x 12 = 60."),
    ("Quantitative", "medium", "A can finish a job in 12 days, B in 18 days. Working together, how many days do they need?",
     ["6.8", "7.2", "7.5", "8"], 1, "Rate = 1/12 + 1/18 = 5/36 per day, so 36/5 = 7.2 days."),
    ("Quantitative", "medium", "Simple interest on Rs. 5000 at 8% per annum for 3 years is:",
     ["Rs. 1000", "Rs. 1200", "Rs. 1500", "Rs. 2000"], 1, "SI = P x R x T / 100 = 5000 x 8 x 3 / 100 = 1200."),
    ("Quantitative", "hard", "How many ways can 5 people sit around a circular table?",
     ["24", "60", "120", "720"], 0, "Circular permutations = (n-1)! = 4! = 24."),
    ("Logical", "easy", "Find the next number: 2, 6, 12, 20, 30, ?", ["40", "42", "44", "48"], 1,
     "Differences are 4, 6, 8, 10, so the next difference is 12: 30 + 12 = 42."),
    ("Logical", "easy", "If all roses are flowers and some flowers fade quickly, which must be true?",
     ["All roses fade quickly", "Some roses fade quickly", "All roses are flowers", "No rose fades quickly"], 2,
     "Only 'all roses are flowers' is given directly; the others do not necessarily follow."),
    ("Logical", "medium", "In a code, CAT = 24 and DOG = 26 (sum of letter positions). What is BAT?",
     ["22", "23", "24", "25"], 1, "The code adds letter positions (CAT = 3+1+20 = 24, DOG = 4+15+7 = 26), so BAT = 2+1+20 = 23."),
    ("Logical", "medium", "Pointing to a man, Riya says 'He is the son of my mother's only brother.' How is he related to Riya?",
     ["Brother", "Cousin", "Uncle", "Nephew"], 1, "Mother's brother's son is Riya's maternal cousin."),
    ("Logical", "hard", "Four friends A, B, C and D stand in a row. A is left of B, C is right of D, and B is left of D. Who stands furthest to the right?",
     ["A", "B", "C", "D"], 2, "The conditions force the order A, B, D, C from left to right, so C is furthest right."),
    ("Verbal", "easy", "Choose the synonym of 'ABUNDANT':", ["Scarce", "Plentiful", "Tiny", "Rare"], 1,
     "Abundant means existing in large quantities, i.e. plentiful."),
    ("Verbal", "easy", "Choose the antonym of 'EXPAND':", ["Grow", "Stretch", "Contract", "Spread"], 2,
     "To contract is to become smaller, the opposite of expand."),
    ("Verbal", "medium", "Fill in the blank: Neither the manager nor the employees ___ aware of the change.",
     ["is", "are", "was", "has been"], 1, "With 'neither...nor', the verb agrees with the nearer subject (employees), so 'are'."),
    ("Verbal", "medium", "Identify the correctly spelled word:",
     ["Accomodate", "Acommodate", "Accommodate", "Acomodate"], 2, "The correct spelling has double c and double m: accommodate."),
    ("Verbal", "hard", "'To beat around the bush' means:",
     ["To search carefully", "To avoid the main point", "To exercise outdoors", "To argue loudly"], 1,
     "The idiom means to avoid talking directly about the main issue."),
]

# (title, difficulty, statement, tests) -- stdin/stdout programs
CODING = [
    ("Sum of Two Numbers", "easy",
     "Read two integers a and b from standard input (space or newline separated) and print their sum.",
     [("3 4", "7"), ("-5 10", "5"), ("0 0", "0"), ("1000000 2000000", "3000000")]),
    ("Reverse a String", "easy",
     "Read a single line of text and print it reversed.",
     [("hello", "olleh"), ("a", "a"), ("OpenAI", "IAnepO"), ("racecar", "racecar")]),
    ("Palindrome Check", "easy",
     "Read a single word. Print YES if it reads the same forwards and backwards (case-insensitive), otherwise NO.",
     [("Level", "YES"), ("hello", "NO"), ("A", "YES"), ("Noon", "YES")]),
    ("FizzBuzz", "easy",
     "Read an integer n. For each number from 1 to n print on its own line: FizzBuzz if divisible by 3 and 5, Fizz if by 3, Buzz if by 5, otherwise the number.",
     [("5", "1\n2\nFizz\n4\nBuzz"), ("15", "\n".join(["1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz", "11", "Fizz", "13", "14", "FizzBuzz"])), ("1", "1")]),
    ("Two Sum (indices)", "medium",
     "First line: n and target. Second line: n integers. Print the 0-based indices i<j of the unique pair whose values sum to target, separated by a space.",
     [("4 9\n2 7 11 15", "0 1"), ("3 6\n3 2 4", "1 2"), ("2 6\n3 3", "0 1"), ("5 -1\n-3 4 3 90 2", "0 4")]),
    ("Longest Increasing Subsequence", "hard",
     "First line: n. Second line: n integers. Print the length of the longest strictly increasing subsequence.",
     [("8\n10 9 2 5 3 7 101 18", "4"), ("6\n0 1 0 3 2 3", "4"), ("4\n7 7 7 7", "1"), ("1\n5", "1")]),
]


def seed():
    db = SessionLocal()
    try:
        if not db.query(Category).count():
            db.add_all([Category(name=n, kind="interview") for n in INTERVIEW_CATEGORIES])
            db.add_all([Category(name=n, kind="aptitude") for n in ["Quantitative", "Logical", "Verbal"]])
        if not db.query(User).filter_by(email="admin@example.com").first():
            db.add(User(name="Admin", email="admin@example.com", password_hash=hash_password("Admin@123"), role="admin"))
        if not db.query(User).filter_by(email="student@example.com").first():
            db.add(User(name="Demo Student", email="student@example.com", password_hash=hash_password("Student@123"),
                        target_role="Software Engineer", skills=["Python", "SQL"]))
        if not db.query(Question).filter_by(kind="aptitude").count():
            for sec, diff, text, opts, ans, exp in APTITUDE:
                db.add(Question(kind="aptitude", category=sec, difficulty=diff, text=text, options=opts,
                                answer_index=ans, explanation=exp))
        if not db.query(Question).filter_by(kind="coding").count():
            for title, diff, text, tests in CODING:
                db.add(Question(kind="coding", category="Coding", difficulty=diff, title=title, text=text,
                                test_cases=[{"input": i, "expected": o} for i, o in tests]))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    from .database import Base, engine
    Base.metadata.create_all(engine)
    seed()
    print("Seeded.")
