import json
import os
import re
import tempfile

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from faster_whisper import WhisperModel
from groq import Groq

from .models import Meeting


# ============================================================
# WHISPER CONFIGURATION
# ============================================================

WHISPER_MODEL_NAME = "tiny"

print("Loading Whisper model...")

whisper_model = WhisperModel(
    WHISPER_MODEL_NAME,
    device="cpu",
    compute_type="int8",
)

print("Whisper model loaded successfully.")


# ============================================================
# GROQ CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GROQ_MODEL_NAME = "openai/gpt-oss-20b"

if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print("Groq API key detected.")
else:
    groq_client = None
    print("WARNING: GROQ_API_KEY is not configured.")


# ============================================================
# WEBSOCKET CONSUMER
# ============================================================

class MeetingConsumer(AsyncWebsocketConsumer):

    async def connect(self):

        self.meeting_id = self.scope["url_route"]["kwargs"]["meeting_id"]

        self.audio_chunks = []

        await self.accept()

        print(
            f"WebSocket connected successfully "
            f"for meeting {self.meeting_id}"
        )

        await self.send(
            text_data="Server: WebSocket connected successfully!"
        )

    async def receive(
        self,
        text_data=None,
        bytes_data=None
    ):

        # ====================================================
        # RECEIVE AUDIO CHUNK
        # ====================================================

        if bytes_data:

            self.audio_chunks.append(bytes_data)

            print(
                f"Server received audio data. "
                f"Chunk size: {len(bytes_data)} bytes"
            )

            return

        # ====================================================
        # RECEIVE TEXT COMMAND
        # ====================================================

        if text_data:

            print(
                f"Server received message: {text_data}"
            )

            # =================================================
            # STOP RECORDING
            # =================================================

            if text_data == "stop_recording":

                print(
                    "Stop recording command received."
                )

                if not self.audio_chunks:

                    await self.send(
                        text_data="ERROR: No audio data received."
                    )

                    print(
                        "No audio chunks available."
                    )

                    return

                # =============================================
                # COMBINE AUDIO
                # =============================================

                complete_audio = b"".join(
                    self.audio_chunks
                )

                print(
                    f"Complete audio received: "
                    f"{len(complete_audio)} bytes"
                )

                await self.send(
                    text_data="STATUS:Transcribing audio..."
                )

                # =============================================
                # TRANSCRIBE
                # =============================================

                transcript = await self.transcribe_audio(
                    complete_audio
                )

                if not transcript:

                    await self.send(
                        text_data="ERROR: No speech detected."
                    )

                    self.audio_chunks = []

                    return

                print(
                    "Whisper transcript:"
                )

                print(transcript)

                await self.send(
                    text_data=f"TRANSCRIPT:{transcript}"
                )

                await self.save_transcript(
                    transcript
                )

                # =============================================
                # GROQ ANALYSIS
                # =============================================

                await self.send(
                    text_data=(
                        "STATUS:"
                        "Analyzing meeting with Groq..."
                    )
                )

                analysis = await self.analyze_with_groq(
                    transcript
                )

                print(
                    "Groq analysis:"
                )

                print(analysis)

                # =============================================
                # SAVE ANALYSIS + TITLE
                # =============================================

                await self.save_analysis(
                    analysis
                )

                print(
                    "Groq analysis saved to database."
                )

                # =============================================
                # SEND ANALYSIS TO BROWSER
                # =============================================

                await self.send(
                    text_data=(
                        "ANALYSIS:"
                        + json.dumps(
                            analysis,
                            ensure_ascii=False
                        )
                    )
                )

                await self.send(
                    text_data=(
                        "STATUS:"
                        "Meeting analysis complete."
                    )
                )

                self.audio_chunks = []

    # ========================================================
    # WHISPER TRANSCRIPTION
    # ========================================================

    async def transcribe_audio(
        self,
        audio_bytes
    ):

        temporary_file_path = None

        try:

            with tempfile.NamedTemporaryFile(
                suffix=".webm",
                delete=False
            ) as temporary_file:

                temporary_file.write(
                    audio_bytes
                )

                temporary_file_path = (
                    temporary_file.name
                )

            print(
                f"Temporary audio file created: "
                f"{temporary_file_path}"
            )

            segments, info = whisper_model.transcribe(

                temporary_file_path,

                beam_size=5,

                vad_filter=True,

                language="en",

                initial_prompt=(
                    "AI Meeting Assistant, "
                    "AI meeting assistant, "
                    "meeting, "
                    "transcription, "
                    "speech to text, "
                    "application, "
                    "software, "
                    "testing, "
                    "project, "
                    "team, "
                    "deadline, "
                    "action items, "
                    "decisions, "
                    "summary, "
                    "Django, "
                    "Python, "
                    "JavaScript, "
                    "Whisper, "
                    "Groq."
                ),
            )

            transcript_parts = []

            for segment in segments:

                text = segment.text.strip()

                if text:

                    transcript_parts.append(
                        text
                    )

            transcript = " ".join(
                transcript_parts
            ).strip()

            print(
                f"Detected language: "
                f"{getattr(info, 'language', 'unknown')}"
            )

            print(
                f"Transcription completed. "
                f"Characters: {len(transcript)}"
            )

            return transcript

        except Exception as error:

            print(
                f"Whisper transcription error: "
                f"{error}"
            )

            return ""

        finally:

            if (
                temporary_file_path
                and os.path.exists(
                    temporary_file_path
                )
            ):

                try:

                    os.remove(
                        temporary_file_path
                    )

                except Exception as error:

                    print(
                        "Could not remove temporary "
                        f"audio file: {error}"
                    )

    # ========================================================
    # GROQ ANALYSIS
    # ========================================================

    async def analyze_with_groq(
        self,
        transcript
    ):

        if not groq_client:

            print(
                "Groq analysis skipped because "
                "GROQ_API_KEY is missing."
            )

            return {

                "title": "Meeting",

                "summary": (
                    "Groq API key is not configured."
                ),

                "decisions": (
                    "None identified."
                ),

                "action_items": (
                    "None identified."
                ),

                "deadlines": (
                    "None identified."
                ),
            }

        system_prompt = """
You are an AI meeting assistant.

Analyze the meeting transcript provided by the user.

Return ONLY a valid JSON object.

The JSON object MUST contain exactly these five fields:

{
    "title": "...",
    "summary": "...",
    "decisions": "...",
    "action_items": "...",
    "deadlines": "..."
}

Rules:

1. title:
   Generate a concise and professional meeting title
   based ONLY on the transcript.

   The title should normally contain between 3 and 8 words.

   Make the title specific to the main subject of the meeting.

   Do not use generic titles such as:
   "New Meeting"
   "Meeting"
   "Team Meeting"
   "Discussion"

   unless the transcript does not contain enough
   information to create a meaningful title.

2. summary:
   Give a concise summary of the meeting.

3. decisions:
   List important decisions that were explicitly made.

   If there are no decisions, return:
   "None identified."

4. action_items:
   List tasks that need to be completed.

   Include the responsible person when the transcript
   provides one.

   If there are no action items, return:
   "None identified."

5. deadlines:
   List dates, days, times, or deadlines mentioned
   in the meeting.

   If there are no deadlines, return:
   "None identified."

Do not invent information.

Use only information contained in the transcript.

Return valid JSON only.
"""

        user_prompt = f"""
Analyze this meeting transcript:

{transcript}
"""

        try:

            print(
                "Sending transcript to Groq..."
            )

            response = groq_client.chat.completions.create(

                model=GROQ_MODEL_NAME,

                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],

                temperature=0,

                reasoning_effort="low",

                include_reasoning=False,

                response_format={
                    "type": "json_object"
                },

                max_completion_tokens=1000,
            )

            message = response.choices[0].message

            raw_response = message.content

            print(
                "Raw Groq response:"
            )

            print(
                raw_response
            )

            if not raw_response:

                print(
                    "Groq returned an empty "
                    "message content."
                )

                return {

                    "title": "Meeting",

                    "summary": (
                        "Groq returned an empty "
                        "analysis response."
                    ),

                    "decisions": (
                        "None identified."
                    ),

                    "action_items": (
                        "None identified."
                    ),

                    "deadlines": (
                        "None identified."
                    ),
                }

            analysis = self.extract_json(
                raw_response
            )

            analysis = self.validate_analysis(
                analysis
            )

            return analysis

        except Exception as error:

            print(
                f"Groq analysis error: {error}"
            )

            return {

                "title": "Meeting",

                "summary": (
                    "An error occurred while "
                    "analyzing the meeting."
                ),

                "decisions": (
                    "None identified."
                ),

                "action_items": (
                    "None identified."
                ),

                "deadlines": (
                    "None identified."
                ),
            }

    # ========================================================
    # EXTRACT JSON
    # ========================================================

    def extract_json(
        self,
        raw_response
    ):

        try:

            cleaned = raw_response.strip()

            cleaned = re.sub(
                r"^```json\s*",
                "",
                cleaned,
                flags=re.IGNORECASE
            )

            cleaned = re.sub(
                r"^```\s*",
                "",
                cleaned
            )

            cleaned = re.sub(
                r"\s*```$",
                "",
                cleaned
            )

            cleaned = cleaned.strip()

            try:

                parsed = json.loads(
                    cleaned
                )

                if isinstance(
                    parsed,
                    dict
                ):

                    return parsed

            except json.JSONDecodeError:

                pass

            start_index = cleaned.find(
                "{"
            )

            end_index = cleaned.rfind(
                "}"
            )

            if (
                start_index != -1
                and end_index != -1
                and end_index > start_index
            ):

                json_text = cleaned[
                    start_index:
                    end_index + 1
                ]

                parsed = json.loads(
                    json_text
                )

                if isinstance(
                    parsed,
                    dict
                ):

                    return parsed

            raise ValueError(
                "No valid JSON object found "
                "in Groq response."
            )

        except Exception as error:

            print(
                f"Groq JSON parsing error: "
                f"{error}"
            )

            return {

                "title": "Meeting",

                "summary": (
                    "Groq returned an invalid "
                    "analysis response."
                ),

                "decisions": (
                    "None identified."
                ),

                "action_items": (
                    "None identified."
                ),

                "deadlines": (
                    "None identified."
                ),
            }

    # ========================================================
    # VALIDATE ANALYSIS
    # ========================================================

    def validate_analysis(
        self,
        analysis
    ):

        if not isinstance(
            analysis,
            dict
        ):

            return {

                "title": "Meeting",

                "summary": (
                    "No valid meeting summary "
                    "was returned."
                ),

                "decisions": (
                    "None identified."
                ),

                "action_items": (
                    "None identified."
                ),

                "deadlines": (
                    "None identified."
                ),
            }

        title = analysis.get(
            "title",
            "Meeting"
        )

        summary = analysis.get(
            "summary",
            "No summary available."
        )

        decisions = analysis.get(
            "decisions",
            "None identified."
        )

        action_items = analysis.get(
            "action_items",
            "None identified."
        )

        deadlines = analysis.get(
            "deadlines",
            "None identified."
        )

        # ====================================================
        # TITLE
        # ====================================================

        if isinstance(
            title,
            list
        ):

            title = " ".join(
                str(item)
                for item in title
            )

        elif not isinstance(
            title,
            str
        ):

            title = str(
                title
            )

        title = title.strip()

        if not title:

            title = "Meeting"

        # ====================================================
        # SUMMARY
        # ====================================================

        if isinstance(
            summary,
            list
        ):

            summary = "\n".join(
                str(item)
                for item in summary
            )

        elif not isinstance(
            summary,
            str
        ):

            summary = str(
                summary
            )

        # ====================================================
        # DECISIONS
        # ====================================================

        if isinstance(
            decisions,
            list
        ):

            decisions = "\n".join(
                str(item)
                for item in decisions
            )

        elif not isinstance(
            decisions,
            str
        ):

            decisions = str(
                decisions
            )

        # ====================================================
        # ACTION ITEMS
        # ====================================================

        if isinstance(
            action_items,
            list
        ):

            action_items = "\n".join(
                str(item)
                for item in action_items
            )

        elif not isinstance(
            action_items,
            str
        ):

            action_items = str(
                action_items
            )

        # ====================================================
        # DEADLINES
        # ====================================================

        if isinstance(
            deadlines,
            list
        ):

            deadlines = "\n".join(
                str(item)
                for item in deadlines
            )

        elif not isinstance(
            deadlines,
            str
        ):

            deadlines = str(
                deadlines
            )

        return {

            "title": title,

            "summary": summary.strip(),

            "decisions": decisions.strip(),

            "action_items": action_items.strip(),

            "deadlines": deadlines.strip(),
        }

    # ========================================================
    # SAVE TRANSCRIPT
    # ========================================================

    @sync_to_async
    def save_transcript(
        self,
        transcript
    ):

        try:

            meeting = Meeting.objects.get(
                id=self.meeting_id
            )

            meeting.transcript = transcript

            meeting.save(
                update_fields=[
                    "transcript",
                    "updated_at",
                ]
            )

            print(
                f"Transcript saved for meeting "
                f"{self.meeting_id}"
            )

        except Meeting.DoesNotExist:

            print(
                f"Meeting {self.meeting_id} "
                f"does not exist."
            )

        except Exception as error:

            print(
                f"Error saving transcript: "
                f"{error}"
            )

    # ========================================================
    # SAVE ANALYSIS + AUTOMATIC TITLE
    # ========================================================

    @sync_to_async
    def save_analysis(
        self,
        analysis
    ):

        try:

            meeting = Meeting.objects.get(
                id=self.meeting_id
            )

            generated_title = analysis.get(
                "title",
                "Meeting"
            )

            if not generated_title:

                generated_title = "Meeting"

            meeting.title = generated_title

            meeting.summary = analysis.get(
                "summary",
                ""
            )

            meeting.decisions = analysis.get(
                "decisions",
                ""
            )

            meeting.action_items = analysis.get(
                "action_items",
                ""
            )

            meeting.deadlines = analysis.get(
                "deadlines",
                ""
            )

            meeting.save(
                update_fields=[
                    "title",
                    "summary",
                    "decisions",
                    "action_items",
                    "deadlines",
                    "updated_at",
                ]
            )

            print(
                f"Analysis and title saved "
                f"for meeting {self.meeting_id}"
            )

            print(
                f"Generated meeting title: "
                f"{generated_title}"
            )

        except Meeting.DoesNotExist:

            print(
                f"Meeting {self.meeting_id} "
                f"does not exist."
            )

        except Exception as error:

            print(
                f"Error saving analysis: "
                f"{error}"
            )

    # ========================================================
    # DISCONNECT
    # ========================================================

    async def disconnect(
        self,
        close_code
    ):

        print(
            f"WebSocket disconnected for meeting "
            f"{getattr(self, 'meeting_id', 'unknown')}. "
            f"Close code: {close_code}"
        )

        self.audio_chunks = []