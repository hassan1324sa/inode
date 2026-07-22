import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_pdf(filename="fluxa_roadmap.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=25
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=15,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.white
    )
    
    done_badge = ParagraphStyle(
        'DoneBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#15803D')
    )
    
    pending_badge = ParagraphStyle(
        'PendingBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#B45309')
    )

    story = []
    
    # Title & Subtitle
    story.append(Paragraph("Fluxa MVP - Implementation Roadmap", title_style))
    story.append(Paragraph("Detailed status report of completed modules and upcoming milestones for the workflow automation platform.", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Overall Progress Table
    progress_data = [
        [Paragraph("<b>Core Phase</b>", table_header_style), Paragraph("<b>Status</b>", table_header_style), Paragraph("<b>Completion %</b>", table_header_style)],
        [Paragraph("Phase 1: Foundation (Config, DB, Health)", body_style), Paragraph("COMPLETED", done_badge), Paragraph("100%", body_style)],
        [Paragraph("Phase 2: Core Data Models (User, Org, Workflow, Exec)", body_style), Paragraph("COMPLETED", done_badge), Paragraph("100%", body_style)],
        [Paragraph("Phase 3: Simple Workflow Node (Set Variable)", body_style), Paragraph("COMPLETED", done_badge), Paragraph("100%", body_style)],
        [Paragraph("Phase 4: Execution Engine (Temporal Orchestration)", body_style), Paragraph("COMPLETED", done_badge), Paragraph("100%", body_style)],
        [Paragraph("Phase 5: User Interface (Frontend Canvas & Logs)", body_style), Paragraph("PENDING", pending_badge), Paragraph("0%", body_style)],
        [Paragraph("Phase 6: Integrations Library (AI, HTTP, Logic)", body_style), Paragraph("PENDING", pending_badge), Paragraph("10%", body_style)],
        [Paragraph("Phase 7: Webhooks & Schedule Triggers", body_style), Paragraph("PENDING", pending_badge), Paragraph("0%", body_style)],
        [Paragraph("Phase 8: Security & Credentials Storage", body_style), Paragraph("PENDING", pending_badge), Paragraph("0%", body_style)],
    ]
    
    t_progress = Table(progress_data, colWidths=[280, 120, 100])
    t_progress.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4F46E5')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('TOPPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOTTOMPADDING', (0,1), (-1,-1), 6),
        ('TOPPADDING', (0,1), (-1,-1), 6),
    ]))
    
    story.append(t_progress)
    story.append(Spacer(1, 20))
    
    # COMPLETED TASKS SECTION
    story.append(Paragraph("Completed Milestones ([X] Done)", section_heading))
    
    done_tasks = [
        [Paragraph("<b>Module</b>", table_header_style), Paragraph("<b>Implementation Details</b>", table_header_style)],
        [Paragraph("Project Config", body_style), Paragraph("Centralized configuration with Pydantic settings loading from env vars.", body_style)],
        [Paragraph("Database Setup", body_style), Paragraph("MongoDB connection + Beanie ODM schemas defined for User, Org, Workflow, WorkflowVersion, Execution, NodeExecution.", body_style)],
        [Paragraph("Health API", body_style), Paragraph("Simple health check endpoint returning system status.", body_style)],
        [Paragraph("Orchestrator", body_style), Paragraph("Shifted from ARQ to Temporal Workflow Orchestrator supporting pause/resume/cancel signals.", body_style)],
        [Paragraph("Temporal Worker", body_style), Paragraph("Worker script executing load_execution_context and execute_node activities.", body_style)],
        [Paragraph("Demo Node", body_style), Paragraph("Set Variable node executor built and registered in NodeExecutorRegistry.", body_style)],
    ]
    
    t_done = Table(done_tasks, colWidths=[150, 350])
    t_done.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_done)
    story.append(PageBreak())
    
    # MISSING FEATURES & ROADMAP SECTION
    story.append(Paragraph("Upcoming Implementation Tasks ([ ] Todo)", section_heading))
    
    todo_tasks = [
        [Paragraph("<b>Task Name</b>", table_header_style), Paragraph("<b>Scope & Requirements</b>", table_header_style), Paragraph("<b>Phase</b>", table_header_style)],
        # Frontend
        [Paragraph("Frontend Workspace Setup", body_style), Paragraph("Initialize Next.js/Vite project for the web interface.", body_style), Paragraph("Frontend", body_style)],
        [Paragraph("Visual Workflow Canvas", body_style), Paragraph("Integrate React Flow to drag and drop nodes, connect edges, and export JSON definitions.", body_style), Paragraph("Frontend", body_style)],
        [Paragraph("Run History & Logs UI", body_style), Paragraph("Real-time execution dashboard showing node status list from MongoDB.", body_style), Paragraph("Frontend", body_style)],
        # Nodes
        [Paragraph("HTTP Request Node", body_style), Paragraph("Create HTTP client node to trigger external API calls (GET, POST, headers, payload).", body_style), Paragraph("Nodes Library", body_style)],
        [Paragraph("AI / LLM Node", body_style), Paragraph("Integrate Gemini / OpenAI model nodes for intelligent text processing.", body_style), Paragraph("Nodes Library", body_style)],
        [Paragraph("Logic Nodes (If/Else)", body_style), Paragraph("Implement conditional branch parsing in Temporal orchestrator workflow.", body_style), Paragraph("Nodes Library", body_style)],
        # Triggers
        [Paragraph("Webhook Trigger Endpoint", body_style), Paragraph("Expose dynamic endpoint `/api/v1/webhooks/{wf_id}` to start a workflow on external events.", body_style), Paragraph("Triggers", body_style)],
        [Paragraph("Cron / Schedule Trigger", body_style), Paragraph("Use Temporal cron or APScheduler to fire manual execution API on schedule.", body_style), Paragraph("Triggers", body_style)],
        # Credentials
        [Paragraph("Secure Vault Storage", body_style), Paragraph("Encryption service using cryptography (Fernet) to store external keys (Slack, Google tokens).", body_style), Paragraph("Security", body_style)],
    ]
    
    t_todo = Table(todo_tasks, colWidths=[140, 260, 100])
    t_todo.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F8FAFC')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_todo)
    
    doc.build(story)
    print("PDF Generated successfully.")

if __name__ == "__main__":
    create_pdf()
