from bs4 import BeautifulSoup
import cohere
from cohere.classify import Example
import requests
from flask import *
import json
import goodExamples
import badExamples

# This stock...
CATEGORIES = ["should be avoided", "will likely lead to a loss",
              "is neutral", "will likely lead to gains", "is an excellent investment opportunity"]

examples = goodExamples.goodExamples+badExamples.badExamples


def ParseForHeadlines(url):
    url = url.lower()
    page = requests.get("https://www.google.com/search?q="+url +
                        "&sxsrf=ALiCzsaSPDrf7gvK_75WAWemS43p92q4JA:1668867145331&source=lnms&tbm=nws&sa=X&ved=2ahUKEwiCrv_Ktrr7AhW4IjQIHdFdC74Q_AUoAXoECAEQAw&biw=1440&bih=821&dpr=2")
    soup = BeautifulSoup(page.content, "html.parser")
    headings = soup.find_all("h3")
    hyperlinks = [a['href'] for a in soup.find_all('a', href=True) if a.text]
    inputs = [i.find("div").text for i in headings]
    hyperlinks = hyperlinks[-6-len(inputs):-6]
    HeadlinesAndUrls = [(inputs[i], hyperlinks[i]) for i in range(len(inputs))]
    # print(HeadlinesAndUrls[5][1][7:])
    return HeadlinesAndUrls


def ClassifyHeadlines(inputs):
    co = cohere.Client('yo3sGBCHSmIUSH3bQJNjzjYobJVka265uNZQ5Q8p')
    response = co.classify(
        model="large",
        inputs=inputs,
        examples=examples,
    )
    return response


def GetSentiment(inputs, response):
    sentiment = 0
    for i in range(len(inputs)):

        # print()
        # print(inputs[i])
        # print(response.classifications[i])
        # print()

        if response.classifications[i].prediction == "negative":
            sentiment -= response.classifications[i].confidence
        if response.classifications[i].prediction == "positive":
            sentiment += response.classifications[i].confidence
    sentiment /= len(inputs)
    return sentiment


def GenerateDescription(inputs, responses):
    co = cohere.Client('yo3sGBCHSmIUSH3bQJNjzjYobJVka265uNZQ5Q8p')
    # "This stock "+CATEGORIES[int(len(CATEGORIES)*sentiment)]
    TEMPLATE = """Generates a summary of the stock evaluation.
Passage: A new venue has been opened.
TLDR: A new venue has been opened.
-
Passage: Black Friday deals you can get.
TLDR: Profits are expected to rise from Black Friday sales.
-
Passage: A new release has been announced.
TLDR: Much-anticipated product offerings are slated for release.
-
"""
    collector = []
    for i in range(len(inputs)):
        if responses.classifications[i].confidence > 0.7:
            prompter = TEMPLATE
            prompter += "Passage: "+inputs[i]+"\n"
            prompter += "TLDR: "
            response = co.generate(
                model='medium',
                prompt=prompter,
                max_tokens=40,
                temperature=0.3,
                frequency_penalty=0.5,
                stop_sequences=[".", ","])
            stock_description = response.generations[0].text
            collector.append(stock_description)
        else:
            collector.append("NULL")
    return collector


# name = "target bad"
# HeadlinesAndUrls = ParseForHeadlines(name)
# titles = [i[0] for i in HeadlinesAndUrls]
# results = ClassifyHeadlines(titles)
# sentiment = GetSentiment(titles, results)
# print(CATEGORIES[int((sentiment+1)/2*len(CATEGORIES))])
# descriptions = GenerateDescription(titles, results)
# response = ClassifyHeadlines(descriptions)
# for i in range(len(descriptions)):
#     if response.classifications[i].confidence > 0.8 and descriptions[i] != "NULL":
#         print(descriptions[i])
#         print(HeadlinesAndUrls[i][1])
#         print()

# Read the Room
# Tough Crowd
# Litmus Test
# Temperature

app = Flask(__name__)


@app.route('/getSentiment', methods=['GET'])
def getInfo():
    data = json.loads(request.data)

    jason = {
        'Bullet_Points': [],
        'links': []
    }
    name = data['Stock_Name']
    HeadlinesAndUrls = ParseForHeadlines(name)
    titles = [i[0] for i in HeadlinesAndUrls]
    results = ClassifyHeadlines(titles)
    sentiment = GetSentiment(titles, results)
    print(CATEGORIES[int((sentiment+1)/2*len(CATEGORIES))])
    descriptions = GenerateDescription(titles, results)
    response = ClassifyHeadlines(descriptions)
    for i in range(len(descriptions)):
        if response.classifications[i].confidence > 0.8 and descriptions[i] != "NULL":
            jason['Bullet_Points'].append(descriptions[i])
            jason['links'].append(HeadlinesAndUrls[i][1])

    jason['ovr_rating'] = int((sentiment+1)/2*len(CATEGORIES))

    print(jason)

    return jason