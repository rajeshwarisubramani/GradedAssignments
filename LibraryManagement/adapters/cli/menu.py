from adapters.cli.handlers import get_service, safe_call


def print_menu() -> None:
    print("\n=== City Library CLI ===")
    print("1) Add book")
    print("2) Register member")
    print("3) Borrow book")
    print("4) Return book")
    print("5) Search books")
    print("6) Available books by genre")
    print("7) Members with borrowed books")
    print("8) Most popular genre")
    print("9) List books")
    print("q) Quit")


def _build_actions(service):
    return {
        "1": lambda: safe_call(
            service.add_book,
            input("Book ID: ").strip(),
            input("Title: ").strip(),
            input("Author: ").strip(),
            input("Genre: ").strip(),
        ),
        "2": lambda: safe_call(
            service.register_member,
            input("Member ID: ").strip(),
            input("Name: ").strip(),
            input("Age: ").strip(),
            input("Contact info: ").strip(),
        ),
        "3": lambda: safe_call(
            service.borrow_book,
            input("Member ID: ").strip(),
            input("Book ID: ").strip(),
        ),
        "4": lambda: safe_call(
            service.return_book,
            input("Member ID: ").strip(),
            input("Book ID: ").strip(),
        ),
        "5": lambda: safe_call(service.search_books, input("Query: ").strip()),
        "6": lambda: safe_call(
            service.report_available_books_by_genre, input("Genre: ").strip()
        ),
        "7": lambda: safe_call(service.report_members_with_borrowed_books),
        "8": lambda: safe_call(service.report_most_popular_genre),
        "9": lambda: safe_call(service.list_books),
    }


def run_cli() -> None:
    service = get_service()
    actions = _build_actions(service)

    while True:
        print_menu()
        choice = input("Choose: ").strip().lower()

        match choice:
            case "q":
                print("Goodbye.")
                break
            case _:
                action = actions.get(choice)
                if action:
                    ok, result = action()
                    print("Success:" if ok else "Error:", result)
                else:
                    print("Invalid option.")


if __name__ == "__main__":
    run_cli()

