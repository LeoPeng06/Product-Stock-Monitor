import streamlit as st
from scrape import scrapeSite, extract_html, cleanBody, splitDomContent

st.title("PokeScraper")
url = st.text_input("Enter the URL of the Site you want to scrape")

if st.button("Scrape"):
    st.write(f"Scraping {url}...")
    result = scrapeSite(url)
    bodyContent = extract_html(result)
    cleanContent = cleanBody(bodyContent)
    
    st.session_state.content = cleanContent

    with st.expander("Scraped Content"):
        st.text_area("Content", st.session_state.content, height=200)
if "dom_content" in st.session_state:
    parseDescription = st.text_area("Enter the description of the content you want to parse")

    if st.button("Parse"):
        if parseDescription:
            st.write(f"Parsing {parseDescription}...")
            domChunks = splitDomContent(st.session_state.content)
            for chunk in domChunks:
                st.write(chunk)

