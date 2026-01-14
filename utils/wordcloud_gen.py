from wordcloud import WordCloud
import matplotlib.pyplot as plt
import os

def generate_wordcloud(comments):

    text = " ".join(comments)

    wc = WordCloud(width=800, height=400, background_color="white").generate(text)

    output_path = "static/wordcloud.png"
    wc.to_file(output_path)

    return output_path
    