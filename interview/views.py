from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Avg
from google import genai
import PyPDF2
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from django.http import HttpResponse
import json
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect

from .models import InterviewSession, InterviewResponse, Resume
from .ai_utils import evaluate_answer

def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("login")
    else:
        form = UserCreationForm()

    return render(request, "signup.html", {"form": form})


def home(request):
    return render(request, "home.html")


@login_required
def start_interview(request):

    # 🔹 STEP 1: If coming from homepage (domain selection)
    if request.method == "POST" and "domain" in request.POST:

        resume_text = request.session.get("resume_text", "")
        selected_domain = request.POST.get("domain", "General")

        session = InterviewSession.objects.create(
            user=request.user,
            resume_text=resume_text,
            current_question_number=1,
            domain=selected_domain
        )

        question = """
Hello 👋 I will be your interviewer today.

To begin with, please introduce yourself and briefly explain your background and key skills.
"""

        return render(request, "interview.html", {
            "question": question.strip(),
            "session_id": session.id
        })

    # 🔹 STEP 2: Get active session
    session = InterviewSession.objects.filter(
        user=request.user,
        is_completed=False
    ).first()

    if not session:
        return redirect("home")

    # 🔹 STEP 3: If answering a question
    if request.method == "POST":
        # 🔴 If user clicked End Interview
        if "end_interview" in request.POST:

            session.is_completed = True
            session.save()

            responses = InterviewResponse.objects.filter(session=session)

            if not responses.exists():
                return render(request, "interview_complete.html", {
                    "average_score": 0,
                    "final_feedback": "Interview ended early. No responses recorded."
                })

            transcript = ""
            total_score = 0
            count = 0

            for r in responses:
                transcript += f"Question: {r.question}\n"
                transcript += f"Answer: {r.answer}\n\n"

                if r.ai_score:
                    total_score += r.ai_score
                    count += 1

            average_score = total_score / count if count > 0 else 0

            final_prompt = f"""
        You are a senior interview panelist.

        The candidate ended the interview early.

        Here is the transcript so far:

        {transcript}

        Provide:

        1. Performance summary based only on available answers
        2. Observed strengths
        3. Observed weaknesses
        4. Hiring recommendation (based on partial interview)
        """

            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            final_response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=final_prompt
            )

            return render(request, "interview_complete.html", {
                "average_score": round(average_score, 2),
                "final_feedback": final_response.text,
                "session_id": session.id
            })
    
            

        answer = request.POST.get("answer")
        last_question = request.POST.get("question_text")

        if not last_question:
            return redirect("start_interview")

        # Evaluate answer
        ai_result = evaluate_answer(last_question, answer)

        InterviewResponse.objects.create(
            session=session,
            question=last_question,
            answer=answer,
            ai_score=ai_result["score"],
            ai_feedback=ai_result["feedback"]
        )

        session.current_question_number += 1

        # 🔹 END INTERVIEW AFTER 8 QUESTIONS
        if session.current_question_number > 8:
            session.is_completed = True
            session.save()

            responses = InterviewResponse.objects.filter(session=session)

            transcript = ""
            total_score = 0
            count = 0

            for r in responses:
                transcript += f"Question: {r.question}\n"
                transcript += f"Answer: {r.answer}\n\n"

                if r.ai_score:
                    total_score += r.ai_score
                    count += 1

            average_score = total_score / count if count > 0 else 0

            final_prompt = f"""
You are a senior interview panelist.

Here is the full interview transcript:

{transcript}

Provide:

1. Overall performance summary
2. Key strengths
3. Key weaknesses
4. Final hiring recommendation
"""

            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            final_response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=final_prompt
            )

            return render(request, "interview_complete.html", {
                "average_score": round(average_score, 2),
                "final_feedback": final_response.text
            })

        session.save()

        # 🔹 Generate next contextual question
        responses = InterviewResponse.objects.filter(session=session)

        conversation_history = ""
        for r in responses:
            conversation_history += f"""
Question: {r.question}
Candidate Answer: {r.answer}
"""

        next_question_prompt = f"""
You are conducting a professional 15-minute {session.domain} job interview.

Candidate Resume:
{session.resume_text}

Conversation so far:
{conversation_history}

Instructions:
- Ask the next logical interview question.
- Avoid repeating previous questions.
- If candidate answer was weak, ask a follow-up.
- If answer was strong, go deeper technically.
- Make it realistic like a human interviewer.
- Do NOT provide feedback.
- Ask ONLY one question.
"""

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=next_question_prompt
        )

        next_question = response.text.strip()

        return render(request, "interview.html", {
            "question": next_question,
            "session_id": session.id
        })

    # 🔹 STEP 4: If GET request (continue interview)
    return render(request, "interview.html", {
        "question": "Please continue your interview.",
        "session_id": session.id
    })


@login_required
def upload_resume(request):
    if request.method == "POST":
        pdf_file = request.FILES.get("pdf")

        resume, created = Resume.objects.update_or_create(
            user=request.user,
            defaults={"pdf": pdf_file}
        )

        # Extract text from PDF
        pdf_reader = PyPDF2.PdfReader(resume.pdf.path)
        text = ""

        for page in pdf_reader.pages:
            text += page.extract_text() or ""

        request.session["resume_text"] = text

        return render(request, "upload_resume.html", {"success": True})

    return render(request, "upload_resume.html")


@login_required
def dashboard(request):

    sessions = InterviewSession.objects.filter(user=request.user)
    total_interviews = sessions.count()

    responses = InterviewResponse.objects.filter(session__user=request.user)
    average_score = responses.aggregate(Avg("ai_score"))["ai_score__avg"]

    session_scores = []

    for session in sessions:
        session_responses = InterviewResponse.objects.filter(session=session)
        avg = session_responses.aggregate(Avg("ai_score"))["ai_score__avg"]
        if avg:
            session_scores.append(round(avg, 2))

    return render(request, "dashboard.html", {
        "total_interviews": total_interviews,
        "average_score": round(average_score, 2) if average_score else 0,
        "session_scores": json.dumps(session_scores)
    })

@login_required
def download_report(request, session_id):

    session = InterviewSession.objects.get(id=session_id, user=request.user)

    responses = InterviewResponse.objects.filter(session=session)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Interview_Report_{session.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    heading_style = styles["Heading1"]

    elements.append(Paragraph("AI Mock Interview Report", heading_style))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph(f"Candidate: {request.user.username}", normal_style))
    elements.append(Paragraph(f"Interview Domain: {session.domain}", normal_style))
    elements.append(Paragraph(f"Date: {session.created_at}", normal_style))
    elements.append(Spacer(1, 0.3 * inch))

    total_score = 0
    count = 0

    for idx, r in enumerate(responses, start=1):
        elements.append(Paragraph(f"<b>Question {idx}:</b> {r.question}", normal_style))
        elements.append(Spacer(1, 0.1 * inch))

        elements.append(Paragraph(f"<b>Answer:</b> {r.answer}", normal_style))
        elements.append(Spacer(1, 0.1 * inch))

        elements.append(Paragraph(f"<b>Score:</b> {r.ai_score}", normal_style))
        elements.append(Spacer(1, 0.3 * inch))

        if r.ai_score:
            total_score += r.ai_score
            count += 1

    average_score = total_score / count if count > 0 else 0

    elements.append(Paragraph(f"<b>Average Score:</b> {round(average_score,2)}", normal_style))
    elements.append(Spacer(1, 0.5 * inch))

    doc.build(elements)

    return response