def load_data():
    return [1, 2, 3]


def normalize(values):
    return [value / max(values) for value in values]


def summarize(values):
    return sum(values) / len(values)


def process_data():
    values = normalize(load_data())
    return summarize(values)


def save_report():
    values = load_data()
    return summarize(values)


def main():
    return process_data(), save_report()
