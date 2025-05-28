import os
import streamlit as st
from dotenv import load_dotenv
from atlassian import Confluence
import google.generativeai as genai
import difflib


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


st.title("🧪 Confluence AI Test Support")


confluence = init_confluence()
ai_model = init_ai()

if confluence:
    space_key = st.text_input("Enter your Confluence space key:")
    
    if space_key:
        try:
            pages = confluence.get_all_pages_from_space(space=space_key, start=0, limit=50)
            titles = [page['title'] for page in pages]
            st.write("📄 Pages available in space:", titles)

            old_page_title = st.text_input("Enter the title of the OLD version code page:")
            new_page_title = st.text_input("Enter the title of the NEW version code page:")

            old_code = ""
            new_code = ""

            if old_page_title and new_page_title:
                for page in pages:
                    if page["title"].strip().lower() == old_page_title.strip().lower():
                        page_data = confluence.get_page_by_id(page["id"], expand="body.storage")
                        old_code = page_data["body"]["storage"]["value"]
                    elif page["title"].strip().lower() == new_page_title.strip().lower():
                        page_data = confluence.get_page_by_id(page["id"], expand="body.storage")
                        new_code = page_data["body"]["storage"]["value"]

                if old_code and new_code:
                    st.success("✅ Both pages fetched successfully!")

                    st.subheader("📜 Old Version")
                    st.code(old_code, language="python")

                    st.subheader("📜 New Version")
                    st.code(new_code, language="python")

                    old_lines = old_code.splitlines()
                    new_lines = new_code.splitlines()
                    diff = difflib.unified_diff(old_lines, new_lines, fromfile=old_page_title, tofile=new_page_title, lineterm='')
                    diff_text = "\n".join(list(diff))

                    prompt = f"""The following is a diff between two versions of a codebase:\n\n{diff_text}\n\nBased on these changes, please suggest appropriate test strategies and test cases.
Include which types of testing should be performed (unit, integration, regression),
what areas require new tests or modifications, and any specific edge cases to consider."""

                    with st.spinner("🔍 Analyzing code changes and generating test strategies..."):
                        response = ai_model.generate_content(prompt)
                        st.success("🧪 Testing support generated!")

                    st.subheader("📋 Suggested Test Strategies and Test Cases")
                    st.markdown(response.text.strip())
                else:
                    st.warning("One or both of the entered page titles do not contain valid content.")
        except Exception as e:
            st.error(f"Error retrieving Confluence data: {str(e)}")
else:
    st.error("❌ Could not connect to Confluence.")
