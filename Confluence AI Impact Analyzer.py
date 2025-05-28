import os
import streamlit as st
from dotenv import load_dotenv
from atlassian import Confluence
import google.generativeai as genai
import difflib
from bs4 import BeautifulSoup


load_dotenv()


genai.configure(api_key="")
model = genai.GenerativeModel("models/gemini-1.5-flash-8b-latest")


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


def extract_code_blocks(content):
    soup = BeautifulSoup(content, 'html.parser')
    code_blocks = soup.find_all('ac:structured-macro', {'ac:name': 'code'})
    extracted_code = []
    for block in code_blocks:
        plain_text = block.find('ac:plain-text-body')
        if plain_text:
            extracted_code.append(plain_text.text)
    return '\n'.join(extracted_code)


st.title("🧠 Confluence AI Impact Analyzer")

confluence = init_confluence()

if confluence:
    st.success("✅ Connected to Confluence")


    space_key = st.text_input("Enter your Confluence Space Key:")
    old_page_title = st.text_input("Enter the OLD version code page title:")
    new_page_title = st.text_input("Enter the NEW version code page title:")

    if space_key and old_page_title and new_page_title:
        try:
            pages = confluence.get_all_pages_from_space(space=space_key, start=0, limit=50)

            old_page = next((p for p in pages if p["title"].strip().lower() == old_page_title.strip().lower()), None)
            new_page = next((p for p in pages if p["title"].strip().lower() == new_page_title.strip().lower()), None)

            if old_page and new_page:
                old_raw = confluence.get_page_by_id(old_page["id"], expand="body.storage")["body"]["storage"]["value"]
                new_raw = confluence.get_page_by_id(new_page["id"], expand="body.storage")["body"]["storage"]["value"]

                old_code = extract_code_blocks(old_raw)
                new_code = extract_code_blocks(new_raw)

                st.subheader(f"📄 {old_page_title} Code")
                st.code(old_code if old_code else "No code blocks found in the old version.", language='python')

                st.subheader(f"📄 {new_page_title} Code")
                st.code(new_code if new_code else "No code blocks found in the new version.", language='python')

                if old_code and new_code:
                    old_lines = old_code.splitlines()
                    new_lines = new_code.splitlines()

                    diff = difflib.unified_diff(
                        old_lines, new_lines, fromfile=old_page_title, tofile=new_page_title, lineterm=''
                    )
                    diff_text = '\n'.join(list(diff))

                    if diff_text.strip():
                        prompt = f"""The following is a diff between two versions of a codebase:\n\n{diff_text}\n\nPlease analyze the changes and provide a summary of potential impacts, including affected modules, functions, and any potential risks introduced by these changes."""
                        response = model.generate_content(prompt)

                        st.subheader("📌 Impact Analysis Summary")
                        st.markdown(response.text.strip())
                    else:
                        st.info("✅ No differences found between the two versions.")
                else:
                    st.warning("⚠️ One or both pages do not contain code blocks.")
            else:
                st.warning("❌ Could not find one or both of the specified pages in the space.")

        except Exception as e:
            st.error(f"Error: {str(e)}")
else:
    st.error("❌ Could not connect to Confluence.")
