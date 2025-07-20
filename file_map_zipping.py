import shutil
import os


REPOSITORY = "D:\example\here"
FILE_EXTENSION_TO_EXTRACT_THE_UNIQUE_LIST = "txt"
file_paths: list[str] = []

uniqueNames = []
allFileNames: list[str] = []
walker = os.walk(REPOSITORY)
for dirpath, dirnames, filenames in walker:
    for fileName in filenames:
        allFileNames.append(fileName)
        if fileName.split(".")[-1] == FILE_EXTENSION_TO_EXTRACT_THE_UNIQUE_LIST:
            # We're in a unique fileName
            uniqueNames.append(fileName.split(".")[0])


for fileToBeMoved in allFileNames:
    splittedName = fileToBeMoved.split(".")
    fileNameWithoutExtension = splittedName[0]
    folderPath = os.path.join(REPOSITORY, fileNameWithoutExtension)

    os.makedirs(folderPath, exist_ok=True)
    print("folder created")

    shutil.move(
        REPOSITORY + f"\\{fileToBeMoved}",
        dst=REPOSITORY + f"\\{splittedName[0]}\\{fileToBeMoved}",
    )

for unique in uniqueNames:
    archive_path = os.path.join(REPOSITORY, unique)

    shutil.make_archive(
        base_name=archive_path,
        root_dir=archive_path,
        format="zip",
    )
