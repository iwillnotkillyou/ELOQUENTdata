import os
import sys, pathlib, pymupdf
import urllib.request
import re
import spacy

def printf(*p):
    print(*p)

pagebreak = "\n----------\n"
sectionbreak = pagebreak
def extract(in_path, out_path_assesment, out_path_rest, is_assesment):
    assesments = ""
    othertext = ""
    first = True
    with pymupdf.open(in_path) as doc:
        for i, a, sb in is_assesment:
            t = doc[i].get_text(sort = True)
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

class Progress:
    def __init__(self):
        self.lastc = 0
    def show_progress(self, block_num, block_size, total_size):
        blockc = total_size/block_size
        c = int(100 * block_num / blockc)
        if c % 10 == 0 and c != self.lastc:
            print(f"{c} percent downloaded")
        self.lastc = c

def get_sources():
    sources = []
    with open("sources.txt") as f:
        for x in f.readlines():
            x = x.strip()
            if x == "":
                return sources
            else:
                sources.append(x)
    return sources

def get_pseudo_summaries(split_text, top_n, exclude = None):
    data = []
    for x in range(len(split_text)):
        data.append(set(split_text[x].split(" ")))

    rs = []
    for x in range(len(data)):
        if exclude is not None and x in exclude:
            continue
        candidate = data[x]
        document = data[:x] + data[x+1:]
        if len(document) == 0:
            return []

        def R1F1(set1, set2):
            inter = len(set1.intersection(set2))
            r = inter / len(set2)
            p = inter / len(set1)
            return 2*r*p/(r+p) if r+p > 0 else 0

        averageR1F1 = sum([R1F1(candidate,x) for x in document]) / len(document)
        rs.append(averageR1F1)

    return [x[0] for x in sorted(enumerate(rs), key = lambda x : x[1])[:top_n]]

def clean_split(text):
    text = re.sub(r"FIGURE[^)]*\)", "", text)
    text = re.sub(r"\(Figure[^)]*\)", "", text)
    rg = r"\A(\s)\s+(\S)|(\S\s)\s+(\S)|(\S\s)\s+()\Z" if False else r"(\S\s)\s+(\S)"
    text = re.sub(rg, r"\1<FORMATTING>\2", text)
    s = text.find("BEYOND THE BOOK")
    printf(text[s:s+200])
    text, n = re.subn("BEYOND THE BOOK[\n.]*<FORMATTING>[\n.]*<FORMATTING>", "", text)
    print("sub", n)
    printf(text.count("BEYOND THE BOOK"))
    return text.split(sectionbreak)


def get_right_subtree(token):
    l = []
    stack = [list(token.rights)[0]]
    while len(stack) > 0:
        t = stack.pop()
        for x in t.children:
            stack.append(x)
            l.append(x)
    return sorted([x.idx for x in l])

class SimpleQuestionMaker:
    def __init__(self):
        r1 = (r"", r"")
        self.regexes = [r1]
        self.nlp = spacy.load("en_core_web_sm")


    def fwd(self, text):
        text = text.replace("<FORMATTING>", "")
        text = re.sub(r"[^\w\s?.!,-]", "", text)
        def make_sentances(text):
            a = text.split(".")
            r = []
            excluded = set()
            for i, x in enumerate(a):
                r.append(x)
                if len(x) < 200:
                    excluded.add(i)
            return r, excluded

        sentances, excluded = make_sentances(text)
        summaries = get_pseudo_summaries(sentances, 10, excluded)
        if not any(summaries):
            raise Exception()
            return ""
        candidates = []
        for x in summaries:
            summary = sentances[x]
            summary = summary.replace("\n", " ")
            printf(summary)
            summary = re.sub(r"\A\s+", "",summary)
            doc = self.nlp(summary)
            #printf([(w.text, w.dep_, w.idx) for w in doc])
            sents = list(doc.sents)
            #printf("sents", len(sents), sents)
            root = sents[0].root
            c = list(root.children)
            #printf([(w.text, w.dep_, w.idx) for w in c])
            for x in c:
                if x.pos_ not in  ["NOUN", "PROPN"]:
                    continue
                quest = "What"
                if x.ent_iob != 2:
                    quest = "Who"
                rl = len(x.right_edge.text_with_ws)
                l = x.left_edge.idx
                r = x.right_edge.idx+rl
                candidates.append(quest + " " + summary[:l] + "."*(r-l) + summary[r:])
                print(candidates[-1])
        return min(candidates, key = lambda x: len(x))

        for x in self.regexes:
            summary = re.sub(x[0], x[1], summary)

def evaluate(text, label, question_maker):
    texts = clean_split(text)
    labels = clean_split(label)
    if False:
        print(texts)
        print("Text:")
        print(texts[1])
        print("Created questions:")
    print(question_maker.fwd(texts[2]))
    #print("True questions:")
    #print(labels[0])



def main():
    for x in get_sources():
        fn = x.split('/')[-1]
        path = f"files/{fn}"
        print(path)
        if not os.path.isfile(path):
            urllib.request.urlretrieve(x, path, Progress().show_progress)
    in_folder = "files"
    out_folder1 = "assessments"
    out_folder2 = "rest"
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