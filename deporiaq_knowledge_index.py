"""Bounded local retrieval supporting thousands of authored help records.

The exact-question map and token index are built once. Answers are never inferred
from a number of keyword hits: only a reviewed card can be returned. Question
forms are paraphrases, not additional topics; diagnostics report both counts.
"""
from collections import defaultdict
from difflib import SequenceMatcher

class GuideIndex:
    def __init__(self,topics,fold):
        self.fold=fold;self.phrases=[];self.by_token=defaultdict(set);self.exact=defaultdict(set);self.questions={}
        seen=set()
        tr=['{t} hakkında yardım','{t} nasıl çalışır','{t} adımlarını anlatır mısın','{t} konusunda ne yapmalıyım','{t} için yardım eder misin','{t} hakkında bilgi istiyorum']
        en=['Help me with {t}','How does {t} work','Explain the steps for {t}','I need help with {t}','Can you explain {t}','Tell me about {t}']
        for topic in topics:
            if topic.key in seen or not topic.body or not topic.body_en:raise ValueError('Invalid or duplicate guide card: '+topic.key)
            seen.add(topic.key)
            forms=[x.format(t=topic.title) for x in tr]+[x.format(t=topic.title_en) for x in en]
            self.questions[topic.key]=tuple(forms)
            for question in forms:self.exact[fold(question)].add(topic.key)
            for phrase in (*topic.phrases,topic.title,topic.title_en):
                terms=frozenset(fold(phrase).split())
                if not terms:continue
                index=len(self.phrases);self.phrases.append((topic.key,terms))
                for term in terms:self.by_token[term].add(index)
        self.topic_count=len(seen);self.question_count=sum(len(v) for v in self.questions.values())
        self.vocabulary=tuple(self.by_token)
    def lookup(self,question):
        if not isinstance(question,str) or not 1<=len(question)<=2000:return ()
        q=self.fold(question)
        if q in self.exact:return tuple(sorted(self.exact[q]))[:3]
        words=set(q.split()[:80]);matched=set();candidates=set()
        for term in self.vocabulary:
            if term in words or (term.isalpha() and any(len(term)>=3 and word.startswith(term) for word in words)):matched.add(term)
            elif term.isalpha() and len(term)>=5 and any(word.isalpha() and len(word)>=5 and abs(len(term)-len(word))<=2 and SequenceMatcher(None,term,word).ratio()>=.84 for word in words):matched.add(term)
        for term in matched:candidates.update(self.by_token[term])
        scores=defaultdict(list)
        for i in candidates:
            key,terms=self.phrases[i]
            if terms.issubset(matched):scores[key].append(len(terms)*6+sum(min(len(t),8) for t in terms)/10)
        ranked=sorted(((max(v)+min(len(v)-1,3)*.2,k) for k,v in scores.items()),key=lambda x:(-x[0],x[1]))
        if not ranked:return ()
        best=ranked[0][0];return tuple(k for score,k in ranked[:3] if score>=best*.78)
