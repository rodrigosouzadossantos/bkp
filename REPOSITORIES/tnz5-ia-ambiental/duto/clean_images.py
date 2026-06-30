import glob
import shutil

if __name__ == '__main__':

    for filename_png in glob.glob("Segmentadas-Duto-2006\**.png"):
        achou = False
        for filename_json in glob.glob("Segmentadas-Duto-2006\**.json"):
            if filename_json.split("/")[-1].split(".")[0] == filename_png.split("/")[-1].split(".")[0]:
                achou = True
                break
        if not achou:
            shutil.move(filename_png, filename_png.replace("Segmentadas-Duto-2006", "Nao-Segmentadas-Duto"))

    for filename_jpg in glob.glob("Segmentadas-Duto-2006\**.jpg"):
        achou = False
        for filename_json in glob.glob("Segmentadas-Duto-2006\**.json"):
            if filename_json.split("/")[-1].split(".")[0] == filename_jpg.split("/")[-1].split(".")[0]:
                achou = True
                break
        if not achou:
            shutil.move(filename_jpg, filename_jpg.replace("Segmentadas-Duto-2006", "Nao-Segmentadas-Duto"))
