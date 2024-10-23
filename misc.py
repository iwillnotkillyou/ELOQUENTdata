import re
import spacy
def printf(*p):
    print(*p)

pagebreak = "\n----------\n"
sectionbreak = pagebreak

def get_sources(path):
    sources = []
    with open(path) as f:
        for x in f.readlines():
            x = x.strip()
            if x == "":
                return sources
            else:
                sources.append(x)
    return sources

def get_right_subtree(token):
    l = []
    stack = [list(token.rights)[0]]
    while len(stack) > 0:
        t = stack.pop()
        for x in t.children:
            stack.append(x)
            l.append(x)
    return sorted([x.idx for x in l])


class Progress:
    def __init__(self):
        self.lastc = 0
    def show_progress(self, block_num, block_size, total_size):
        blockc = total_size/block_size
        c = int(100 * block_num / blockc)
        if c % 10 == 0 and c != self.lastc:
            print(f"{c} percent downloaded")
        self.lastc = c

class SimpleQuestionMaker:
    def __init__(self, extra_break = None):
        r1 = (r"", r"")
        self.regexes = [r1]
        self.nlp = spacy.load("en_core_web_sm")
        self.extra_break = extra_break


    def summary(self, text, lencheck, topn, maxlen = 1000):
        def make_sentances(text):
            if self.extra_break is not None:
                a = text.split(self.extra_break)
            else:
                a = text.split(".")
            newa = []
            for x in a:
                while len(x) > maxlen:
                    x, v = x[maxlen:], x[:maxlen]
                    newa.append(v)
                newa.append(x)
            a = newa
            la = [len(x) for x in a]
            #printf(min(la), max(la), sum(la), sum(la)/len(la))
            r = []
            excluded = set()
            for i, x in enumerate(a):
                r.append(x)
                if len(x) < lencheck:
                    excluded.add(i)
            return r, excluded

        sentances, excluded = make_sentances(text)
        summaries = get_pseudo_summaries(sentances, topn, excluded)
        return summaries, sentances, excluded

    def fwd(self, text):

        text = text.replace("<FORMATTING>", "")
        text = re.sub(r"[^\w\s?.!,-]", "", text)
        summaries, sentances, excluded = self.summary(text, 200, 10)
        if not any(summaries):
            return None
        candidates = []
        for x in summaries:
            summary = sentances[x]
            summary = summary.replace("\n", " ")
            printf(summary)
            summary = re.sub(r"\A\s+", "",summary)
            doc = self.nlp(summary)
            #printf([(w.text, w.dep_, w.idx) for w in doc])
            sents = list(doc.sents)
            if len(sents) == 0:
                return None
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

def extract_words(t):
    t = re.sub(r"(\w)\W+(\w)", r"\1 \2", t)
    t = re.sub(r"\A\W+(\w)", r"\1", t)
    t = re.sub(r"(\w)\W+\Z", r"\1", t)
    return t

def get_pseudo_summaries(split_text, top_n, exclude = None):
    data = []
    for x in range(len(split_text)):
        t = extract_words(split_text[x])
        ds = set(t.split(" "))
        data.append(ds)

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