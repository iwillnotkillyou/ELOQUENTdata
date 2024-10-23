import os
import sys, pathlib, pymupdf
import urllib.request
import re
import spacy
from misc import SimpleQuestionMaker, Progress, printf, get_sources, sectionbreak

def extract(in_path, out_path_assesment, out_path_rest, is_assesment):
    assesments = ""
    othertext = ""
    first = True
    with pymupdf.open(in_path) as doc:
        for i, a, sb in is_assesment:
            d = doc[i].get_textpage().extractDICT(sort = True)
            t = ""
            ls = []
            for x in d['blocks'][:-1]:
                for y in x['lines']:
                    l = " ".join([z['text'] for z in y['spans']])
                    ls.append(l)
                    t += l + "\n"
            t = t.replace("Access for free at openstax.org", "")
            if a:
                if sb:
                    t = t.split("\nAssessments\n")
                    assesments += ("" if first else sectionbreak) + t[1]
                    othertext += t[0] + sectionbreak
                    first = False
                else:
                    assesments += t
            else:
                 othertext += t
    othertext = othertext[:-len(sectionbreak)]
    # write as a binary file to support non-ASCII characters
    out_path_assesment.write_bytes(assesments.encode())
    out_path_rest.write_bytes(othertext.encode())

toc_pages = [6, 7, 8, 9]

def get_assignment_pages(in_path, toc_pages):
    with pymupdf.open(in_path) as doc:
        s = ""
        for page in toc_pages:
            p = doc[page]
            s += p.get_text()
        l = s.split("\n")
        assesments = [x for x in enumerate(l) if x[1] == "Assessments"]
        def m(x):
            next_digit = int(next(y for y in l[x[0] + 2:] if y.isdigit()))
            return int(l[x[0] + 1]), next_digit
        assesments_bounds = [m(x) for x in assesments]
        l = []
        for i in range(9, assesments_bounds[-1][-1]):
            l.append((i+9, any(x[1] > i >= x[0] for x in assesments_bounds), any(i == x[0] for x in assesments_bounds)))
        printf(l)
        return l

def clean_split(text):
    text = re.sub(r"FIGURE[^)]*\)", "", text)
    text = re.sub(r"\(Figure[^)]*\)", "", text)
    rg = r"\A(\s)\s+(\S)|(\S\s)[\s•]+(\S)|(\S\s)\s+()\Z" if True else r"(\S[\s•])[\s•]+(\S)"
    text = re.sub(rg, r"\1<FORMATTING>\2", text)
    s = text.find("BEYOND THE BOOK")
    text, n = re.subn(r"(BEYOND THE BOOK|THE PAST MEETS THE PRESENT|DUELING VOICES|LINK TO LEARNING|IN THEIR OWN WORDS)\n[^\n]*\n", "\n", text)
    print("sub", n)
    return text.split(sectionbreak)

def evaluate(text, label, question_maker):
    texts = clean_split(text)
    labels = clean_split(label)
    for x in texts[1:]:
        print(question_maker.fwd(x, 400))



def main():
    in_folder = "data/files"
    os.makedirs(in_folder, exist_ok=True)
    for x in get_sources("sources_history.txt"):
        fn = x.split('/')[-1]
        path = in_folder+f"/{fn}"
        print(path)
        if not os.path.isfile(path):
            urllib.request.urlretrieve(x, path, Progress().show_progress)
    out_folder1 = "data/assessments"
    out_folder2 = "data/rest"
    os.makedirs(out_folder1, exist_ok=True)
    os.makedirs(out_folder2, exist_ok=True)
    rewrite = False
    for filename in os.listdir(in_folder):
        in_path = pathlib.Path(in_folder).joinpath(filename)
        out_path_rest = pathlib.Path(out_folder2).joinpath(filename + ".txt")
        out_path_assessment = pathlib.Path(out_folder1).joinpath(filename + ".txt")
        if rewrite or not os.path.isfile(out_path_rest) or not os.path.isfile(out_path_assessment):
            is_assesment = get_assignment_pages(in_path, toc_pages)
            extract(in_path, out_path_assessment, out_path_rest, is_assesment)
        with open(out_path_assessment) as f_assessment:
            with open(out_path_rest) as f_rest:
                evaluate(f_rest.read(), f_assessment.read(), SimpleQuestionMaker())

if __name__ == "__main__":
    main()