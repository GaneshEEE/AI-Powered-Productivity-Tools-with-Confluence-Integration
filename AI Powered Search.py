import os
import streamlit as st
from dotenv import load_dotenv
from atlassian import Confluence
import google.generativeai as genai

load_dotenv()

@st.cache_resource
def init_confluence():
    try:
        return Confluence(
            url=os.getenv('CONFLUENCE_BASE_URL'),
            username=os.getenv('CONFLUENCE_USER_EMAIL'),
            password=os.getenv('CONFLUENCE_API_KEY'),
            timeout=10
        )
    except Exception as e:
        st.error(f"Confluence initialization failed: {str(e)}")
        return None

def init_ai():
    genai.configure(api_key="")
    return genai.GenerativeModel("models/gemini-1.5-flash-8b-latest")

st.title("🔗 Confluence AI Powered Search")

confluence = init_confluence()
ai_model = init_ai()

page_found = False
context = ""

if confluence:
    st.success("✅ Connected to Confluence!")

    space_key = st.text_input("Enter your space key:")
    page_title = st.text_input("Enter the page title:")

    if space_key and page_title:
        try:
            pages = confluence.get_all_pages_from_space(space=space_key, start=0, limit=25)
            st.write("📄 Pages in Space:", [p["title"] for p in pages])

            selected_page = None
            for page in pages:
                if page["title"].strip().lower() == page_title.strip().lower():
                    selected_page = page
                    break

            if selected_page:
                page_id = selected_page["id"]
                page_content = confluence.get_page_by_id(page_id, expand="body.storage")
                context = page_content["body"]["storage"]["value"]
                page_found = True
                st.success(f"✅ Found page '{page_title}'!")
                st.write(f"📄 Page Content:\n{context}")
            else:
                st.warning(f"No page titled '{page_title}' found in space '{space_key}'.")

        except Exception as e:
            st.error(f"Error fetching page: {str(e)}")
else:
    st.error("❌ Connection to Confluence failed.")


if confluence and page_found:
    st.subheader("Generate AI Response")
    query = st.text_input("Enter your question:")

    if st.button("Generate Answer"):
        if query and context:
            response = ai_model.generate_content(
                f"Question: {query}\nContext: {context}\nAnswer the question accurately using both the given context and any relevant general knowledge you have. Keep the response concise (max 2 sentences) and also mention the contextual response first followed by the general knowledge."
            )
            st.write(f"**Answer:** {response.text.strip()}")
        else:
            st.error("Please provide a query.")
