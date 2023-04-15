import os
import nltk
import requests
import re
from nltk.corpus import words

api_key = "your_google_books_api_key_here"

class Book:
    def __init__(self, name, path, title, author, date, isbn, scanned):
        self.name = name
        self.path = path
        self.title = title
        self.author = author
        self.date = date
        self.isbn = isbn
        self.scanned = scanned


def download_words():
    current_dir = os.getcwd()
    nltk.data.path.append(current_dir)
    if not os.path.exists(os.path.join(current_dir, "corpora", "words", "en")):
        nltk.download("words", download_dir=current_dir)
        print()


def choose_op_mode():
    print("Library or single folder mode?")
    print("Library mode loops through all folders in a parent directory [l]")
    print("Single mode processes a single folder or file of your choice [s]")
    while True:
        op_input = input("Enter 'l' or 's': ").lower()
        if op_input == "l":
            op_mode = "library"
            break
        elif op_input == "s":
            op_mode = "single"
            break
        else:
            print("Invalid input. Please try again.")
    return op_mode


def get_lib_source_dir():
    print()
    while True:
        lib_source_dir = input("Enter your library source directory: ")
        if os.path.exists(lib_source_dir):
            break
        else:
            print("Invalid directory. Please try again.")
    return lib_source_dir


def get_single_source():
    print()
    while True:
        single_source = input("Enter your single source directory or file: ").lower()
        if os.path.exists(single_source):
            break
        else:
            print("Invalid directory. Please try again.")


def get_skip():
    print()
    while True:
        skip_input = input("Skip books that have already been processed? [y/n]: ").lower()
        if skip_input == "y":
            skip = True
            break
        elif skip_input == "n":
            skip = False
            break
        else:
            print("Invalid input. Please try again.")
    return skip


def check_processed(name):
    try:
        with open("process_log.txt", "r") as f:
            processed_books = [line.strip() for line in f]
    except FileNotFoundError:
            print("Log file not found.")
            return False
    return name in processed_books
    

def add_log(name):
    with open("process_log.txt", "a") as f:
        f.write(name + "\n")


def library_scan(lib_source_dir, skip):
    print()
    for entry in sorted(os.scandir(lib_source_dir), key=lambda e: e.name):
        if skip:
            if check_processed(entry.name):
                print(f"{entry.name} found in process log. Skipping.")
                continue
        working_book = create_book(entry)
        print_working_book(working_book)
        search_choice = get_search_choice()
        if search_choice == "e":
            edit_search(working_book)
        if search_choice != "s":
            search_books(working_book)
            subfolders = get_folder_structure(working_book)
            proc_mode = get_proc_mode()
            if proc_mode == "symlink":
                if 'library_path' not in locals():
                    library_path = get_library_path()
                if subfolders == False:
                    symlink_book(working_book, library_path)
                if subfolders == True:
                    symlink_book_sub(working_book, library_path)


def single_scan(folder_source_dir):
    print()
    working_book = create_book(folder_source_dir)
    if folder_source_dir.is_file():
        working_book.path = folder_source_dir.parent
    print(working_book.name)
    print(working_book.path)

def create_book(entry):
    book = Book(entry.name, entry.path, "", "", "", "", False)
    name_string = entry.name
    if entry.is_file():
        name_string = entry.name.split(".", 1)[0]
    name_string = clean_name_string(name_string)
    title, author = split_name_string(name_string)
    book.title = title
    book.author = author
    return book
    

def clean_name_string(name_string):
    pattern = r'[\{\(\[][^)]*[\)\]\}]'
    clean_name = re.sub(pattern, '', name_string)
    pattern = r'\d{4}([-./])\d{2}\1\d{2}|\d{2}([-./])\d{2}\2\d{4}|\d{4}([-./])\d{1,2}\3\d{1,2}|\d{1,2}([-./])\d{1,2}\4\d{2,4}'
    clean_name = re.sub(pattern, '', clean_name)
    pattern = r'\w*\d+\w*'
    clean_name = re.sub(pattern, '', clean_name)
    pattern = r'\s{2,}'
    clean_name = re.sub(pattern, ' ', clean_name)
    return clean_name


def split_name_string(clean_name):
    title = "" 
    author = ""
    if "by" in clean_name:
        name_parts = clean_name.split("by", maxsplit=1)
        title = name_parts[0]
        author = name_parts[1].lstrip()
    elif "-" in clean_name:
        name_parts = clean_name.split("-", maxsplit=1)
        word_list = set(words.words())
        counta = sum(1 for word in name_parts[0].lower().split() if word in word_list)
        countb = sum(1 for word in name_parts[1].lower().split() if word in word_list)
        if counta > countb:
            title = name_parts[0]
            author = name_parts[1].lstrip()
        elif countb > counta:
            title = name_parts[1].lstrip()
            author = name_parts[0]
        else:
            title = name_parts[0]
            author = name_parts[1].lstrip()
    else:
        title = clean_name.lstrip()
    return title, author


def get_search_choice():
    while True:
        search_input = input("\nPress enter to use this info for search, 'e' to edit, or 's' to skip this folder: ")
        if search_input == "s":
            print()
        if search_input == "" or search_input == "e" or search_input == "s":
            break
        else:
            print("Invalid input. Please try again.")
    return search_input
 

def print_working_book(book):
    print("-" * 50)
    print("Name: " + book.name)
    print("Title: " + book.title)
    print("Author: " + book.author)


def edit_search(book):
    while True:
        book.title = input("Enter title: ")
        book.author = input("Enter author: ")
        if book.title or book.author:
            break
        else:
            print("Please enter title, author, or both.")


def search_books(book):
    while True:
        query = gen_query(book)
        url = f'https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}'
        response = requests.get(url)
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            break
        else:
            print("\nNo results found. Please try again.\n")
            edit_search(book)
    print("\nResults:")
    for i in range(min(5, len(data["items"]))):
        found_book = data["items"][i]["volumeInfo"]
        book_info = get_book_info(found_book)
        print_search_results(book_info, i)
    while True: 
        u_select = input("\nEnter the number of your selection, 's' to skip, or 'e' to edit search query: ")
        if u_select != "s" and u_select != "e" and not u_select.isdigit():
            print("Invalid input. Please try again.")
        else:
            print()
            break
    if u_select == "e":
        edit_search(book)
        search_books(book)
    if u_select != "s" and u_select.isdigit() and int(u_select) <= len(data["items"]):
        foundbook = data["items"][int(u_select)-1]["volumeInfo"]
        print(f'Chosen Book: Title: {foundbook["title"]}, Author: {", ".join(foundbook["authors"])}, Pub Date: {foundbook["publishedDate"]}')
        book.title = foundbook["title"]
        book.author = foundbook["authors"][0]
        book.date = foundbook["publishedDate"]
        print()


def gen_query(book):
    if book.title and book.author:
        query = f'intitle:{book.title}+inauthor:{book.author}'
    elif book.title:
        query = f'intitle:{book.title}'
    elif book.author:
        query = f'inauthor:{book.author}'
    return query


def get_book_info(book):
    book_info = {}
    if "publishedDate" in book:
        book_info["date"] = book["publishedDate"]
    else:
        book_info["date"] = "N/A"
    if "authors" in book:
        book_info["author"] = ", ".join(book["authors"])
    else:
        book_info["author"] = "N/A"
    if "title" in book:
        book_info["title"] = book["title"]
    else:  
        book_info["title"] = "N/A"
    return book_info


def print_search_results(book_info, i):
    print(f'[{i+1}]: Title: {book_info["title"]}, Author: {book_info["author"]}, Pub Date: {book_info["date"]}')


def get_folder_structure(book):
    subdetected = False
    subfolders = False
    if os.path.isdir(book.path):
        for entry in os.scandir(book.path):
            if entry.is_dir():
                subdetected = True
        while subdetected == True:
            subinput = input("Subfolders detected. Proceed in subfolder mode? [y/n]: ")
            if subinput == "y":
                subfolders = True
                break
            elif subinput == "n":
                subfolders = False
                break
            else:
                print("Invalid input. Please try again.")
    return subfolders


def get_proc_mode():
    print("Choose your processing mode:")
    print("[1]: Symlink mode - creates symlinks of audio files in a library folder of your choice.")
    print("[2]: Combine mode - combines all .mp3 files to a single .m4b file in library folder.")
    while True:
        proc_choice = input("Enter [1] or [2]: ")
        if proc_choice == "1":
            proc_mode = "symlink"
            break
        elif proc_choice == "2":
            proc_mode = "combine"
            break
        else:
            print("Invalid input. Please try again.")
    return proc_mode    


def get_library_path():
    while True:
        library_path = input("\nEnter your library path: ")
        if os.path.exists(library_path) and os.path.isdir(library_path):
            break
        else:
            print("Invalid directory. Please try again.")
    return library_path


def symlink_book(book, library_path):
    book_path = os.path.join(library_path, book.author, book.title)
    make_dir(book_path)
    val_extensions = [".mp3", ".m4b", ".m4a", ".flac", ".ogg", ".wav"]
    done = True
    if os.path.isdir(book.path):
        files = sorted(os.listdir(book.path))
        file_count = 0
        for file in files:
            file_ext = os.path.splitext(file)[1]
            if file_ext in val_extensions:
                file_count += 1
        seq_count = 1
        for file in files:
            file_ext = os.path.splitext(file)[1]
            if file_ext in val_extensions:
                seq_num = str(seq_count).zfill(3)
                if file_count > 1:
                    new_name = f"{book.title} - {book.author} - {seq_num}.mp3"
                else:
                    new_name = f"{book.title} - {book.author}.{file_ext}"
                link_path = os.path.join(book_path, new_name)
                try:
                    os.symlink(os.path.join(book.path, file), link_path)
                except FileExistsError:
                    print("Symlink already exists. Skipping to next book in library.\n")
                    done = False
                seq_count += 1
        if done == True:
            print("Symlinks created.\n")
            add_log(book.name)
    elif os.path.isfile(book.path):
        file_ext = os.path.splitext(book.path)[1]
        new_name = f"{book.title} - {book.author}{file_ext}"
        try:
            os.symlink(book.path, os.path.join(book_path, new_name))
            print("Symlink created.\n")
            add_log(book.name)
        except FileExistsError:
            print("Symlink already exists. Skipping to next book in library.\n")


def symlink_book_sub(book, library_path):
    book_path = os.path.join(library_path, book.author, book.title)
    make_dir(book_path)
    val_extensions = [".mp3", ".m4b", ".m4a", ".flac", ".ogg", ".wav"]
    done = True
    file_count = 0
    seq_count = 1
    for dirpath, dirnames, filenames in os.walk(book.path):
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            file_ext = os.path.splitext(filename)[1]
            if file_ext in val_extensions:
                file_count += 1
        for filename in filenames:
            file_ext = os.path.splitext(filename)[1]
            if file_ext in val_extensions:
                seq_num = str(seq_count).zfill(3)
            if file_count > 1:
                new_name = f"{book.title} - {book.author} - {seq_num}.mp3"
            else:
                new_name = f"{book.title} - {book.author}.mp3"
            link_path = os.path.join(book_path, new_name)
            try:
                os.symlink(os.path.join(dirpath, filename), link_path)
            except FileExistsError:
                print("Symlink already exists. Skipping to next book in library.\n")
                done = False
            seq_count += 1
    if done == True:
        print("Symlinks created.\n")
        add_log(book.name)


def make_dir(book_path):
    while not os.path.exists(book_path):
        try:
            os.makedirs(book_path)
        except OSError:
            print("Error creating book directory. Try fixing library permissions.")
            cont_input = input("Press enter to try again. ")


if __name__ == "__main__":
    
    download_words()

    op_mode = choose_op_mode()

    if op_mode == "library":
        lib_source_dir = get_lib_source_dir()
        skip = get_skip()
        library_scan(lib_source_dir, skip)
    elif op_mode == "single":
        single_source = get_single_source()
        single_scan(single_source)

