from app.exceptions import ShortUrlError
from app.repository import ShortUrlRepository
from app.service import ShortUrlService


def run() -> None:
    repository = ShortUrlRepository()
    service = ShortUrlService(repository=repository)

    while True:
        print("\n1. Create short URL")
        print("2. Resolve short URL")
        print("3. View URL details")
        print("4. List URLs")
        print("5. Delete URL")
        print("6. Exit")

        choice = input("Choose an option: ").strip()

        try:
            if choice == "1":
                destination_url = input(
                    "Destination URL: "
                ).strip()

                custom_code = input(
                    "Custom code, or leave blank: "
                ).strip()

                short_url = service.create_url(
                    destination_url=destination_url,
                    custom_code=custom_code or None,
                )

                print(
                    f"Created short code: "
                    f"{short_url.short_code}"
                )

            elif choice == "2":
                short_code = input(
                    "Short code: "
                ).strip()

                short_url = service.resolve_url(short_code)

                print(
                    f"Redirect to: "
                    f"{short_url.destination_url}"
                )

            elif choice == "3":
                short_code = input(
                    "Short code: "
                ).strip()

                short_url = service.get_url_details(
                    short_code
                )

                print(short_url)

            elif choice == "4":
                urls = service.list_urls()

                if not urls:
                    print("No short URLs found.")

                for short_url in urls:
                    print(short_url)

            elif choice == "5":
                short_code = input(
                    "Short code: "
                ).strip()

                service.delete_url(short_code)
                print("Short URL deleted.")

            elif choice == "6":
                print("Goodbye.")
                break

            else:
                print("Invalid option.")

        except ShortUrlError as error:
            print(f"Error: {error}")


if __name__ == "__main__":
    run()
