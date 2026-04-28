from create_gif import fetch_metrics


def main():
    metrics = fetch_metrics()
    if metrics is None:
        print("Data fetching failed. Please check your environment variables and try again.")
        return

    for item in metrics:
        print(
            f"{item['period']}: {item['roi']:+.1f}% | {item['trades']} trades | "
            f"now={item['value_now']:.4f} | now_cash={item['cash_now']:.4f} | "
            f"now_positions={item['positions_now']:.4f} | then={item['value_then']:.4f} | "
            f"then_cash={item['cash_then']:.4f} | then_positions={item['positions_then']:.4f}"
        )


if __name__ == "__main__":
    main()
