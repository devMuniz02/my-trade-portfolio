from create_gif import fetch_metrics


def main():
    metrics = fetch_metrics()
    if metrics is None:
        print("Data fetching failed. Please check your environment variables and try again.")
        return

    for item in metrics:
        print(f"{item['period']}: {item['roi']:+.1f}% | {item['trades']} trades")


if __name__ == "__main__":
    main()
