import os
import json
import base64
import tempfile
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import openai
import anthropic
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

load_dotenv()

DEMO_TOKEN     = os.getenv("DEMO_TOKEN", "zepur2025")
OPENAI_KEY     = os.getenv("OPENAI_API_KEY")
ANTHROPIC_KEY  = os.getenv("ANTHROPIC_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Sarah (neutral, clara)

openai_client     = openai.OpenAI(api_key=OPENAI_KEY)
anthropic_client  = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_KEY)

SYSTEM_PROMPT = """You are an admissions assistant for Tennessee Tech University (AdmitSpace).
Your role is to help prospective students with questions about applications, deadlines,
requirements, financial aid, and campus life. Be warm, concise (2-3 sentences max), and
speak naturally since your responses will be read aloud.

=== ABOUT TENNESSEE TECH ===
- Public research university in Cookeville, Tennessee, founded in 1915
- Enrollment: ~10,000 students (undergraduate + graduate)
- Known for strong engineering, computer science, and business programs
- NCAA Division I athletics (Ohio Valley Conference)
- Campus size: 235 acres in the Upper Cumberland region

=== ACADEMICS ===
Colleges:
- College of Engineering (top-ranked in Tennessee)
- College of Business
- College of Arts & Sciences
- College of Education
- College of Interdisciplinary Studies
- Whitson-Hester School of Nursing

Popular majors: Mechanical Engineering, Electrical Engineering, Computer Science,
Business Administration, Nursing, Biology, Education

Student-to-faculty ratio: 19:1
Average class size: 26 students
Honors program available for high-achieving students

=== ADMISSIONS REQUIREMENTS ===
Freshman requirements:
- High school diploma or GED
- Minimum GPA: 2.5 (competitive applicants average 3.4)
- ACT: 21+ recommended (test-optional through 2025)
- SAT: 1060+ recommended (test-optional through 2025)
- Application essay (personal statement)
- 2 letters of recommendation

Transfer requirements:
- Minimum 2.0 college GPA
- Official transcripts from all previous institutions
- 24+ transferable credit hours preferred

International students:
- TOEFL: 61+ (iBT) or IELTS: 6.0+
- Financial support documentation
- Translated transcripts with certified evaluation

=== APPLICATION DEADLINES ===
Fall semester:
- Priority deadline: March 1st (recommended for scholarships)
- Regular deadline: August 1st (domestic students)
- International deadline: March 15th

Spring semester:
- Priority deadline: October 1st
- Regular deadline: December 1st

Applications submitted after deadlines are reviewed on a rolling basis if space allows.

=== TUITION & FEES (2024-2025) ===
Undergraduate:
- In-state tuition: $9,828/year
- Out-of-state tuition: $27,468/year
- Room & board (on-campus): ~$10,200/year
- Books & supplies estimate: ~$1,200/year
- Total in-state cost of attendance: ~$22,000/year
- Total out-of-state cost of attendance: ~$40,000/year

Graduate:
- In-state: $11,040/year
- Out-of-state: $28,440/year

=== FINANCIAL AID & SCHOLARSHIPS ===
FAFSA school code: 003523
Financial aid priority deadline: February 15th

Tennessee state programs (for TN residents):
- Tennessee Promise: tuition-free community college + up to 2 years at TTU
- Tennessee Student Assistance Award (TSAA): need-based grant
- HOPE Scholarship: requires 3.0 GPA and 21 ACT

TTU Merit Scholarships:
- Presidential Scholarship: full tuition (requires 3.75 GPA + 30 ACT)
- Dean's Scholarship: $6,000/year (requires 3.5 GPA + 27 ACT)
- Eagle Scholarship: $4,000/year (requires 3.25 GPA + 24 ACT)
- Departmental scholarships available through each college

Work-study and on-campus employment widely available.

=== HOUSING ===
On-campus residence halls:
- Roaden University Center (freshmen preferred)
- Jobe Hall, Bartoo Hall, Swim Hall (upperclassmen)
- Suite-style and traditional options
- Average cost: $5,800-$6,400/year

Off-campus housing available in Cookeville (affordable rent ~$600-900/month for apartments).
Freshmen are not required to live on campus.

=== CAMPUS LIFE ===
- 200+ student organizations and clubs
- Greek life: 17 fraternities and sororities
- Intramural sports and recreation center
- Student newspaper: The Oracle
- Annual events: Homecoming, Engineer's Week, Campus Beautification Day
- Cookeville is a safe, mid-sized city with outdoor recreation nearby (hiking, lakes)

=== IMPORTANT CONTACTS ===
Admissions Office:
- Email: admissions@tntech.edu
- Phone: (931) 372-3888
- Hours: Monday-Friday 8am-4:30pm CST
- Address: Derryberry Hall, 1 William L Jones Dr, Cookeville, TN 38505

Financial Aid Office:
- Email: financialaid@tntech.edu
- Phone: (931) 372-3073

Housing Office:
- Email: housing@tntech.edu
- Phone: (931) 372-3177

Website: tntech.edu/admissions
Virtual tour: tntech.edu/visit

=== GUIDELINES ===
- Always be warm, encouraging, and concise (2-3 sentences max per response).
- If unsure about specific details, recommend contacting admissions directly.
- Speak naturally — responses are read aloud to the student.
- Never fabricate specific statistics or policies not listed above.
- NEVER use markdown, bullet points, asterisks, bold text, or line breaks.
- Write in plain natural sentences only, as if speaking to someone face to face.
- Do not start responses with filler phrases like "Great question!" or "Of course!".
"""

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Whisper STT: convierte audio a texto."""
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        with open(tmp_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        return transcript.text.strip()
    finally:
        os.unlink(tmp_path)


async def get_llm_response(conversation_history: list) -> str:
    import re
    message = anthropic_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=conversation_history
    )
    text = message.content[0].text
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def text_to_speech(text: str) -> bytes:
    """ElevenLabs TTS: convierte texto a audio MP3."""
    audio_generator = elevenlabs_client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=text,
        model_id="eleven_turbo_v2",
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        )
    )
    audio_bytes = b"".join(audio_generator)
    return audio_bytes


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    # Verificar token antes de aceptar
    if token != DEMO_TOKEN:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    conversation_history = []

    # Saludo inicial
    greeting = "Hi! I'm the Tennessee Tech admissions assistant. How can I help you today?"
    greeting_audio = await text_to_speech(greeting)
    await websocket.send_json({
        "type": "greeting",
        "text": greeting,
        "audio": base64.b64encode(greeting_audio).decode()
    })

    try:
        while True:
            data = await websocket.receive()

            # Audio crudo (bytes) → STT
            if "bytes" in data:
                audio_bytes = data["bytes"]
                await websocket.send_json({"type": "status", "message": "Transcribing..."})

                user_text = await transcribe_audio(audio_bytes)
                if not user_text:
                    await websocket.send_json({"type": "status", "message": "Didn't catch that, try again."})
                    continue

                await websocket.send_json({"type": "user_text", "text": user_text})

                # Agregar al historial y llamar al LLM
                conversation_history.append({"role": "user", "content": user_text})
                await websocket.send_json({"type": "status", "message": "Thinking..."})

                bot_text = await get_llm_response(conversation_history)
                conversation_history.append({"role": "assistant", "content": bot_text})

                # TTS
                await websocket.send_json({"type": "status", "message": "Generating voice..."})
                bot_audio = await text_to_speech(bot_text)

                await websocket.send_json({
                    "type": "bot_response",
                    "text": bot_text,
                    "audio": base64.b64encode(bot_audio).decode()
                })

            # Texto plano (para pruebas sin micrófono)
            elif "text" in data:
                msg = json.loads(data["text"])
                if msg.get("type") == "text_input":
                    user_text = msg.get("text", "").strip()
                    if not user_text:
                        continue

                    conversation_history.append({"role": "user", "content": user_text})
                    bot_text = await get_llm_response(conversation_history)
                    conversation_history.append({"role": "assistant", "content": bot_text})
                    bot_audio = await text_to_speech(bot_text)

                    await websocket.send_json({
                        "type": "bot_response",
                        "text": bot_text,
                        "audio": base64.b64encode(bot_audio).decode()
                    })

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
