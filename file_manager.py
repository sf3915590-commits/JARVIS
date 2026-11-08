import os


# ==========================================
# TAHRUN FILE MANAGER
# ==========================================

def get_folder(folder_name):

    home = os.path.expanduser("~")

    folders = {
        "downloads": os.path.join(home, "Downloads"),
        "documents": os.path.join(home, "Documents"),
        "desktop": os.path.join(home, "Desktop"),
        "pictures": os.path.join(home, "Pictures"),
        "videos": os.path.join(home, "Videos"),
        "music": os.path.join(home, "Music"),
    }

    return folders.get(folder_name.lower())


def open_folder(folder_name):

    folder = get_folder(folder_name)

    if not folder:
        print("❌ Folder identify nahi hua.")
        return False

    if not os.path.exists(folder):
        print("❌ Folder nahi mila:", folder)
        return False

    try:
        os.startfile(folder)

        print("📁 Folder opened:", folder)

        return True

    except Exception as error:

        print("❌ Folder open error:", error)

        return False


def search_files(search_text, search_location=None):

    if not search_location:
        search_location = os.path.expanduser("~")

    search_text = search_text.lower()

    results = []

    print("\n🔎 File search:", search_text)

    try:

        for root, dirs, files in os.walk(search_location):

            for filename in files:

                if search_text in filename.lower():

                    full_path = os.path.join(
                        root,
                        filename
                    )

                    results.append(full_path)

                    print("📄", full_path)

                    # First 20 results only
                    if len(results) >= 20:
                        return results

    except PermissionError:

        pass

    except Exception as error:

        print("❌ Search error:", error)

    return results


def open_file(file_path):

    if not os.path.exists(file_path):

        print("❌ File nahi mili.")

        return False

    try:

        os.startfile(file_path)

        print("📄 File opened:", file_path)

        return True

    except Exception as error:

        print("❌ File open error:", error)

        return False


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    print("📁 Tahrun File Manager")
    print("----------------------")

    print(
        "Downloads:",
        get_folder("downloads")
    )

    print(
        "Documents:",
        get_folder("documents")
    )
# ==========================================
# PDF READER
# ==========================================

def read_pdf(file_path):
    import PyPDF2

    if not os.path.exists(file_path):
        print("❌ PDF nahi mili:", file_path)
        return False, ""

    try:
        with open(file_path, "rb") as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""

            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        print("📕 PDF read complete:", file_path)
        print("📄 Pages:", len(reader.pages))

        return True, text

    except Exception as error:
        print("❌ PDF read error:", error)
        return False, ""
