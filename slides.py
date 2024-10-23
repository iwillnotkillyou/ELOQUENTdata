import os
import sys, pathlib, pymupdf
import urllib.request
import re
import spacy
from misc import SimpleQuestionMaker, Progress, printf, get_sources, sectionbreak, extract_words
import pymupdf4llm
import pathlib

def main():
    in_folder = "data/files_slides"
    os.makedirs(in_folder, exist_ok=True)
    for x in get_sources("sources_slides.txt"):
        fn = x.split('/')[-1]
        path = in_folder+f"/{fn}"
        print(path)
        if not os.path.isfile(path):
            urllib.request.urlretrieve(x, path, Progress().show_progress)
    out_folder1 = "data/data_present"
    out_folder2 = "data/rest"
    os.makedirs(out_folder1, exist_ok=True)
    os.makedirs(out_folder2, exist_ok=True)
    allt = [[]]
    add_title_for_invalid = False
    for filename in os.listdir(in_folder):
        in_path = pathlib.Path(in_folder).joinpath(filename)

        with pymupdf.open(in_path) as doc:
            for i in range(len(doc)-1):
                if any(doc[i].find_tables()):
                    continue
                d = doc[i].get_textpage().extractDICT(sort=True)
                t = ""
                ls = []
                for x in d['blocks'][:-1]:
                    for y in x['lines']:
                        l = " ".join([z['text'] for z in y['spans']])
                        ls.append(l)
                        t += l + "\n"
                if sum([1 for x in t if x.isdigit()]) > len(t)/10:
                    if add_title_for_invalid:
                        allt[-1].append(ls[0])
                    continue
                if sum([1 for x in ls if len(x) > 10]) < len(ls)*0.8:
                    if add_title_for_invalid:
                        allt[-1].append(ls[0])
                    continue
                good_lines = [x for x in ls if x[0] == "•" or x[0] == "-" or x[0].isdigit()]
                if len(good_lines) < len(ls)*0.4:
                    allt[-1].append("\n".join([ls[0]] + good_lines))
                    continue
                allt[-1].append(t)
        allt.append([])
    pathlib.Path("data/slides_extracted.txt").write_bytes("\n\n\n".join(["\n".join(x) for x in allt]).encode())

    for pages in allt:
        alltext = ".".join([extract_words(x) for x in pages])
        question_maker = SimpleQuestionMaker()
        s = question_maker.summary(alltext, 10, 20, 1000)
        print("\n".join([s[1][x] for x in s[0]]))
        print("\n")

if __name__ == "__main__":
    main()