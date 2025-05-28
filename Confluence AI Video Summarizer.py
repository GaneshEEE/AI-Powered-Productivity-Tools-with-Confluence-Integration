import os
import streamlit as st
from dotenv import load_dotenv
from atlassian import Confluence
import google.generativeai as genai
from moviepy.editor import VideoFileClip
from faster_whisper import WhisperModel


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


st.title("🔗 Confluence AI Video Summarizer")


confluence = init_confluence()
ai_model = init_ai()

if confluence:
    st.success("✅ Connected to Confluence!")
    try:
        space_key = st.text_input("Enter your space key:")
        page_title = st.text_input("Enter the title of the page that contains the video:")

        if space_key and page_title:
            pages = confluence.get_all_pages_from_space(space=space_key, start=0, limit=50)
            selected_page = None

          
            for page in pages:
                if page["title"].strip().lower() == page_title.strip().lower():
                    selected_page = page
                    break

            if selected_page:
                st.success(f"📄 Found page: '{selected_page['title']}'")
                page_id = selected_page["id"]
                page_content = confluence.get_page_by_id(page_id, expand="body.storage")
                video_content = page_content["body"]["storage"]["value"]
                st.write("📝 Page Content:")
                st.markdown(video_content, unsafe_allow_html=True)

             
                video_file_name = "your_video.mp4"  
                try:
                    attachments = confluence.get(f"/rest/api/content/{page_id}/child/attachment")
                    video_url = None
                    for attachment in attachments["results"]:
                        if attachment["title"] == video_file_name:
                            video_url = attachment["_links"]["download"]
                            break

                    if video_url:
                        base_url = os.getenv("CONFLUENCE_BASE_URL").rstrip("/")
                        full_video_url = f"{base_url}{video_url}"

                        video_path = "your_video.mp4"
                        video_data = confluence._session.get(full_video_url).content
                        with open(video_path, "wb") as f:
                            f.write(video_data)

                        st.success("🎥 Video downloaded successfully!")

                     
                        video = VideoFileClip(video_path)
                        video.audio.write_audiofile("test_audio.mp3")

                
                        model = WhisperModel("small", device="cpu", compute_type="int8")
                        segments, _ = model.transcribe("test_audio.mp3")

                        with open("transcription.txt", "w") as file:
                            for segment in segments:
                                file.write(segment.text + " ")

                        st.success("✅ Transcription completed!")

                
                        with open("transcription.txt", "r") as file:
                            text = file.read()

                        response = ai_model.generate_content(
                            f"Summarize this text in points (Include as much detail as needed):\n\n{text}"
                        )

                        with open("summary.txt", "w") as file:
                            file.write(response.text)

                        st.success("✅ Summary created!")
                        st.subheader("📝 Video Summary:")
                        st.markdown(response.text)

                    else:
                        st.error(f"No video file named '{video_file_name}' found in attachments.")
                except Exception as e:
                    st.error(f"Error processing video: {str(e)}")
            else:
                st.warning("⚠️ Page not found with the provided title.")
    except Exception as e:
        st.error(f"Error fetching pages: {str(e)}")
else:
    st.error("❌ Connection to Confluence failed.")
