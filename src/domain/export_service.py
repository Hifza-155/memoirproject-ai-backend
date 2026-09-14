"""
@file domain/export_service.py
@description Business logic for compiling memoir exports, PDF generation,
and storage management using xhtml2pdf.
"""

import html
import io

from xhtml2pdf import pisa

from src.domain.authorization import verify_active_participant
from src.integrations.export_repository import ExportRepository
from src.integrations.storage_adapter import create_playback_url


class ExportService:

    @classmethod
    def initiate_export(cls, memoir_id: str, user_id: str) -> dict:
        """Validates permissions and queues a new PDF export job."""
        participant = verify_active_participant(
            memoir_id,
            user_id,
            required_roles=["owner", "admin", "contributor"]
        )

        participant_id = participant.get("id")

        job = ExportRepository.create_export_job(
            memoir_id,
            participant_id,
            kind="pdf"
        )

        return {
            "export_id": job["id"],
            "memoir_id": memoir_id,
            "status": "queued",
            "message": "Export job queued successfully. Processing in background.",
            "created_at": job["created_at"]
        }

    @classmethod
    def process_export_background(cls, export_id: str, memoir_id: str) -> None:
        """
        Background worker method to compile memoir data, generate the PDF,
        upload it to storage, and update the export job status.
        """
        try:
            # 1. Fetch structured memoir payload.
            payload = ExportRepository.fetch_memoir_export_payload(memoir_id)

            memoir = payload["memoir"]
            participants = payload["participants"]
            memories = payload["memories"]
            memory_media = payload["memory_media"]
            media_assets = payload["media_assets"]
            transcripts = payload["transcripts"]

            # 2. Build the memoir HTML.
            html_content = cls._render_memoir_html(
                memoir=memoir,
                participants=participants,
                memories=memories,
                memory_media=memory_media,
                media_assets=media_assets,
                transcripts=transcripts,
            )

            # 3. Compile HTML to PDF bytes using the existing xhtml2pdf flow.
            pdf_buffer = io.BytesIO()

            pisa_status = pisa.CreatePDF(
                html_content,
                dest=pdf_buffer
            )

            if pisa_status.err:
                raise Exception(
                    "Failed to compile HTML into PDF using xhtml2pdf."
                )

            pdf_bytes = pdf_buffer.getvalue()

            # 4. Upload generated PDF to existing Supabase Storage flow.
            storage_key = (
                f"exports/pdf-archives/{memoir_id}/{export_id}.pdf"
            )

            ExportRepository.upload_pdf_to_storage(
                storage_key,
                pdf_bytes
            )

            # 5. Mark export job as ready.
            ExportRepository.update_job_status(
                export_id=export_id,
                status="ready",
                storage_key=storage_key,
                byte_size=len(pdf_bytes)
            )

        except Exception as e:
            ExportRepository.update_job_status(
                export_id=export_id,
                status="failed",
                error_message=str(e)
            )

    @staticmethod
    def _render_memoir_html(
        memoir: dict,
        participants: list,
        memories: list,
        memory_media: list,
        media_assets: list,
        transcripts: list,
    ) -> str:
        """
        Builds the complete memoir PDF HTML.

        Structure:
        1. Cover
        2. Table of Contents
        3. Written Memories
        4. Voice Memories
        5. Media Memories
        6. Ending page
        """

        # ---------------------------------------------------------
        # Helper functions
        # ---------------------------------------------------------

        def safe(value) -> str:
            """Safely escape database text before placing it into HTML."""
            if value is None:
                return ""

            return html.escape(str(value))

        def format_date(value) -> str:
            """Formats a stored date/datetime value for the PDF."""
            if not value:
                return ""

            value = str(value)

            if "T" in value:
                value = value.split("T")[0]

            return value

        def participant_name(participant_id: str) -> str:
            """Finds a contributor's display name from memoir participants."""
            for participant in participants:
                if participant.get("id") == participant_id:
                    return (
                        participant.get("display_name")
                        or participant.get("email")
                        or "A family member"
                    )

            return "A family member"

        def participant_relationship(participant_id: str) -> str:
            """Finds a contributor's relationship to the memoir subject."""
            for participant in participants:
                if participant.get("id") == participant_id:
                    return participant.get("relationship") or ""

            return ""

        # Map media asset IDs to their database records.
        media_by_id = {
            media.get("id"): media
            for media in media_assets
            if media.get("id")
        }

        # Map transcript media IDs to transcript records.
        transcript_by_media_id = {
            transcript.get("media_asset_id"): transcript
            for transcript in transcripts
            if transcript.get("media_asset_id")
        }

        # Map each memory to its related media.
        media_by_memory_id = {}

        for relation in memory_media:
            memory_id = relation.get("memory_id")
            media_asset_id = relation.get("media_asset_id")

            if not memory_id or not media_asset_id:
                continue

            media = media_by_id.get(media_asset_id)

            if not media:
                continue

            media_by_memory_id.setdefault(memory_id, []).append(media)

        # ---------------------------------------------------------
        # Memoir metadata
        # ---------------------------------------------------------

        subject_name = (
            memoir.get("subject_name")
            or "A Life Remembered"
        )

        description = (
            memoir.get("description")
            or "A collection of memories, voices, and moments."
        )

        born_on = memoir.get("subject_born_on")
        died_on = memoir.get("subject_died_on")
        is_living = memoir.get("subject_is_living")

        years = ""

        if born_on:
            birth_year = str(born_on)[:4]

            if is_living:
                years = birth_year
            elif died_on:
                death_year = str(died_on)[:4]
                years = f"{birth_year} — {death_year}"

        # ---------------------------------------------------------
        # Written memory pages
        # ---------------------------------------------------------

        written_memory_pages = ""

        for memory in memories:
            memory_id = memory.get("id")

            title = safe(
                memory.get("title")
                or "A Memory"
            )

            body = safe(
                memory.get("body_text")
                or ""
            ).replace("\n", "<br />")

            date = format_date(
                memory.get("occurred_start")
                or memory.get("created_at")
            )

            author_id = memory.get("author_participant_id")

            author_name = safe(
                participant_name(author_id)
            )

            relationship = safe(
                participant_relationship(author_id)
            )

            contributor_line = author_name

            if relationship:
                contributor_line += f" · {safe(relationship)}"

            written_memory_pages += f"""
            <div class="memory-page">
                <div class="decorative-top-rule"></div>

                <div class="memory-label">
                    WRITTEN MEMORY
                </div>

                {f'<div class="memory-date">{safe(date)}</div>' if date else ''}

                <h2 class="memory-title">
                    {title}
                </h2>

                <div class="contributor">
                    Remembered by {contributor_line}
                </div>

                <div class="memory-divider"></div>

                <div class="memory-body">
                    {body}
                </div>
            </div>
            """

        # ---------------------------------------------------------
        # Voice memory pages
        # ---------------------------------------------------------

        voice_memory_pages = ""

        for memory in memories:
            related_media = media_by_memory_id.get(
                memory.get("id"),
                []
            )

            for media in related_media:
                if media.get("kind") != "audio":
                    continue

                media_id = media.get("id")
                transcript = transcript_by_media_id.get(
                    media_id,
                    {}
                )

                transcript_text = safe(
                    transcript.get("raw_text")
                    or ""
                ).replace("\n", "<br />")

                duration_ms = media.get("duration_ms")

                duration_text = ""

                if duration_ms is not None:
                    try:
                        total_seconds = int(duration_ms) // 1000
                        minutes = total_seconds // 60
                        seconds = total_seconds % 60
                        duration_text = f"{minutes}:{seconds:02d}"
                    except (TypeError, ValueError):
                        duration_text = ""

                author_id = memory.get("author_participant_id")

                author_name = safe(
                    participant_name(author_id)
                )

                relationship = safe(
                    participant_relationship(author_id)
                )

                contributor_line = author_name

                if relationship:
                    contributor_line += f" · {relationship}"

                voice_title = safe(
                    memory.get("title")
                    or "Voice Memory"
                )

                voice_memory_pages += f"""
                <div class="voice-page">
                    <div class="decorative-top-rule"></div>

                    <div class="memory-label">
                        VOICE MEMORY
                    </div>

                    <h2 class="memory-title">
                        {voice_title}
                    </h2>

                    <div class="contributor">
                        Remembered by {contributor_line}
                    </div>

                    <div class="voice-note">
                        <div class="microphone-circle">
                            MIC
                        </div>

                        <div class="voice-note-content">
                            <div class="voice-note-label">
                                VOICE RECORDING
                            </div>

                            <div class="waveform">
                                ━ ━━━ ━━━━ ━━ ━━━━━ ━━ ━━━
                            </div>
                        </div>

                        <div class="voice-duration">
                            {safe(duration_text)}
                        </div>
                    </div>

                    {
                        f'''
                        <div class="transcript-heading">
                            TRANSCRIPT
                        </div>

                        <div class="transcript">
                            {transcript_text}
                        </div>
                        '''
                        if transcript_text
                        else
                        '''
                        <div class="no-transcript">
                            Transcript not available for this recording.
                        </div>
                        '''
                    }
                </div>
                """

        # ---------------------------------------------------------
        # Media memory pages
        # ---------------------------------------------------------

        media_memory_pages = ""

        for memory in memories:
            related_media = media_by_memory_id.get(
                memory.get("id"),
                []
            )

            if not related_media:
                continue

            memory_id = memory.get("id")

            title = safe(
                memory.get("title")
                or "Media Memory"
            )

            body = safe(
                memory.get("body_text")
                or ""
            ).replace("\n", "<br />")

            author_id = memory.get("author_participant_id")

            author_name = safe(
                participant_name(author_id)
            )

            relationship = safe(
                participant_relationship(author_id)
            )

            contributor_line = author_name

            if relationship:
                contributor_line += f" · {relationship}"

            media_items_html = ""

            for media in related_media:
                kind = media.get("kind")
                caption = safe(
                    media.get("caption")
                    or ""
                )

                storage_key = media.get("storage_key")

                playback_url = None

                if storage_key:
                    playback_url = create_playback_url(
                        storage_key
                    )

                # Photos can be rendered directly in the PDF.
                if kind == "photo" and playback_url:
                    media_items_html += f"""
                    <div class="media-item">
                        <img
                            class="memory-photo"
                            src="{safe(playback_url)}"
                            alt="Memory photograph"
                        />

                        {
                            f'''
                            <div class="media-caption">
                                {caption}
                            </div>
                            '''
                            if caption
                            else ""
                        }
                    </div>
                    """

                # Videos cannot be played/rendered by xhtml2pdf.
                # Represent them as a designed video-memory card.
                elif kind == "video":
                    filename = safe(
                        media.get("original_filename")
                        or "Video memory"
                    )

                    media_items_html += f"""
                    <div class="video-card">
                        <div class="video-icon">
                            ▶
                        </div>

                        <div class="video-content">
                            <div class="video-label">
                                VIDEO MEMORY
                            </div>

                            <div class="video-name">
                                {filename}
                            </div>

                            {
                                f'''
                                <div class="media-caption">
                                    {caption}
                                </div>
                                '''
                                if caption
                                else ""
                            }
                        </div>
                    </div>
                    """

            media_memory_pages += f"""
            <div class="media-page">
                <div class="decorative-top-rule"></div>

                <div class="memory-label">
                    MEDIA MEMORY
                </div>

                <h2 class="memory-title">
                    {title}
                </h2>

                <div class="contributor">
                    Remembered by {contributor_line}
                </div>

                <div class="memory-divider"></div>

                {media_items_html}

                {
                    f'''
                    <div class="media-story">
                        {body}
                    </div>
                    '''
                    if body
                    else ""
                }
            </div>
            """

        # ---------------------------------------------------------
        # Table of contents
        # ---------------------------------------------------------

        toc_items = ""

        for index, memory in enumerate(memories, start=1):
            title = safe(
                memory.get("title")
                or "A Memory"
            )

            toc_items += f"""
            <div class="toc-item">
                <span>{index:02d}</span>
                <span>{title}</span>
            </div>
            """

        # ---------------------------------------------------------
        # Empty-state content
        # ---------------------------------------------------------

        if not written_memory_pages:
            written_memory_pages = """
            <div class="empty-page">
                <div class="memory-label">
                    WRITTEN MEMORIES
                </div>

                <p>
                    This story is still being written.
                </p>
            </div>
            """

        if not voice_memory_pages:
            voice_memory_pages = """
            <div class="empty-page">
                <div class="memory-label">
                    VOICE MEMORIES
                </div>

                <p>
                    No voice memories were included in this collection.
                </p>
            </div>
            """

        if not media_memory_pages:
            media_memory_pages = """
            <div class="empty-page">
                <div class="memory-label">
                    MEDIA MEMORIES
                </div>

                <p>
                    No media memories were included in this collection.
                </p>
            </div>
            """

        # ---------------------------------------------------------
        # Final HTML document
        # ---------------------------------------------------------

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">

            <style>

                @page {{
                    size: A4;
                    margin: 14mm 13mm 16mm 13mm;
                }}

                body {{
                    font-family: Helvetica, Arial, sans-serif;
                    color: #4a3430;
                    background-color: #FBF8F1;
                    margin: 0;
                    padding: 0;
                    line-height: 1.55;
                }}

                .page-border {{
                    border: 1px solid #8B6A3E;
                    padding: 18px;
                }}

                .cover-page {{
                    height: 245mm;
                    border: 1.5px solid #8B6A3E;
                    text-align: center;
                    padding: 20mm 15mm;
                    page-break-after: always;
                }}

                .cover-inner {{
                    border: 1px solid #B79A68;
                    height: 100%;
                    padding: 12mm;
                }}

                .cover-kicker {{
                    font-size: 9pt;
                    letter-spacing: 3px;
                    color: #765548;
                    margin-top: 35mm;
                    margin-bottom: 25mm;
                }}

                .cover-page h1 {{
                    font-size: 30pt;
                    color: #5A252A;
                    margin: 0 0 15px 0;
                }}

                .cover-years {{
                    font-size: 12pt;
                    color: #8B6A3E;
                    margin-bottom: 28px;
                }}

                .cover-description {{
                    font-size: 11pt;
                    color: #765548;
                    font-style: italic;
                    line-height: 1.7;
                    padding: 0 25mm;
                }}

                .cover-rule {{
                    width: 55%;
                    border-top: 1px solid #B79A68;
                    margin: 25px auto;
                }}

                .cover-footer {{
                    font-size: 8pt;
                    letter-spacing: 2px;
                    color: #8B6A3E;
                    margin-top: 35mm;
                }}

                .section-page {{
                    page-break-after: always;
                    min-height: 245mm;
                    border: 1.5px solid #8B6A3E;
                    padding: 15mm;
                }}

                .section-heading {{
                    font-size: 22pt;
                    color: #5A252A;
                    margin: 15mm 0 8mm 0;
                }}

                .section-subtitle {{
                    font-size: 10pt;
                    color: #8B6A3E;
                    font-style: italic;
                    margin-bottom: 18mm;
                }}

                .toc-item {{
                    border-bottom: 1px solid #D9CCB8;
                    padding: 9px 0;
                    font-size: 10pt;
                }}

                .toc-item span:first-child {{
                    color: #8B6A3E;
                    margin-right: 12px;
                }}

                .memory-page {{
                    page-break-after: always;
                    min-height: 245mm;
                    border: 1.5px solid #8B6A3E;
                    padding: 15mm;
                }}

                .voice-page {{
                    page-break-after: always;
                    min-height: 245mm;
                    border: 1.5px solid #8B6A3E;
                    padding: 15mm;
                }}

                .media-page {{
                    page-break-after: always;
                    min-height: 245mm;
                    border: 1.5px solid #8B6A3E;
                    padding: 15mm;
                }}

                .decorative-top-rule {{
                    width: 100%;
                    border-top: 1px solid #B79A68;
                    margin-bottom: 15mm;
                }}

                .memory-label {{
                    font-size: 8pt;
                    letter-spacing: 2.5px;
                    color: #765548;
                    margin-bottom: 7px;
                }}

                .memory-date {{
                    font-size: 8pt;
                    color: #8B6A3E;
                    margin-bottom: 8px;
                }}

                .memory-title {{
                    font-size: 19pt;
                    color: #5A252A;
                    margin: 5px 0 8px 0;
                }}

                .contributor {{
                    font-size: 8.5pt;
                    color: #8B6A3E;
                    font-style: italic;
                    margin-bottom: 15px;
                }}

                .memory-divider {{
                    border-top: 1px solid #D9CCB8;
                    margin: 12px 0 18px 0;
                }}

                .memory-body {{
                    font-size: 10.5pt;
                    color: #4A3430;
                    line-height: 1.75;
                }}

                .voice-note {{
                    background-color: #5A252A;
                    padding: 13px;
                    margin: 25px 0;
                    border: 1px solid #8B6A3E;
                }}

                .microphone-circle {{
                    display: inline-block;
                    background-color: #FBF8F1;
                    color: #5A252A;
                    border: 1px solid #B79A68;
                    width: 35px;
                    height: 35px;
                    text-align: center;
                    padding-top: 10px;
                    font-size: 7pt;
                }}

                .voice-note-content {{
                    display: inline-block;
                    width: 62%;
                    padding-left: 12px;
                    vertical-align: top;
                }}

                .voice-note-label {{
                    color: #FBF8F1;
                    font-size: 7pt;
                    letter-spacing: 2px;
                }}

                .waveform {{
                    color: #D8BC83;
                    font-size: 11pt;
                    margin-top: 5px;
                    white-space: nowrap;
                }}

                .voice-duration {{
                    display: inline-block;
                    color: #FBF8F1;
                    font-size: 8pt;
                    vertical-align: top;
                    padding-top: 13px;
                }}

                .transcript-heading {{
                    font-size: 8pt;
                    letter-spacing: 2px;
                    color: #765548;
                    margin: 18px 0 8px 0;
                }}

                .transcript {{
                    background-color: #F2EAE2;
                    border-left: 3px solid #765548;
                    padding: 13px 15px;
                    font-size: 10pt;
                    line-height: 1.7;
                }}

                .no-transcript {{
                    color: #8B6A3E;
                    font-style: italic;
                    font-size: 9pt;
                    margin-top: 20px;
                }}

                .media-item {{
                    text-align: center;
                    margin: 10px 0 18px 0;
                }}

                .memory-photo {{
                    max-width: 155mm;
                    max-height: 135mm;
                }}

                .media-caption {{
                    font-size: 8.5pt;
                    color: #765548;
                    font-style: italic;
                    margin-top: 7px;
                }}

                .video-card {{
                    background-color: #F2EAE2;
                    border: 1px solid #B79A68;
                    padding: 15px;
                    margin: 12px 0;
                }}

                .video-icon {{
                    display: inline-block;
                    color: #5A252A;
                    font-size: 18pt;
                    width: 35px;
                    vertical-align: top;
                }}

                .video-content {{
                    display: inline-block;
                    width: 80%;
                }}

                .video-label {{
                    font-size: 7pt;
                    letter-spacing: 2px;
                    color: #765548;
                }}

                .video-name {{
                    font-size: 10pt;
                    color: #5A252A;
                    margin-top: 4px;
                }}

                .media-story {{
                    border-top: 1px solid #D9CCB8;
                    margin-top: 18px;
                    padding-top: 15px;
                    font-size: 10pt;
                    line-height: 1.7;
                }}

                .empty-page {{
                    page-break-after: always;
                    min-height: 245mm;
                    border: 1.5px solid #8B6A3E;
                    padding: 15mm;
                    text-align: center;
                    padding-top: 80mm;
                }}

                .empty-page p {{
                    color: #765548;
                    font-style: italic;
                }}

                .ending-page {{
                    min-height: 245mm;
                    border: 1.5px solid #8B6A3E;
                    text-align: center;
                    padding: 20mm 15mm;
                }}

                .ending-inner {{
                    border: 1px solid #B79A68;
                    height: 100%;
                    padding: 15mm;
                }}

                .ending-kicker {{
                    font-size: 8pt;
                    letter-spacing: 3px;
                    color: #765548;
                    margin-top: 45mm;
                }}

                .ending-title {{
                    font-size: 27pt;
                    color: #5A252A;
                    margin: 18px 0;
                }}

                .ending-name {{
                    font-size: 17pt;
                    color: #765548;
                    margin-top: 25px;
                }}

                .ending-years {{
                    font-size: 10pt;
                    color: #8B6A3E;
                    margin-top: 5px;
                }}

                .ending-message {{
                    font-size: 11pt;
                    font-style: italic;
                    color: #765548;
                    line-height: 1.8;
                    margin: 30mm 20mm 0 20mm;
                }}

                .ending-rule {{
                    width: 45%;
                    border-top: 1px solid #B79A68;
                    margin: 25px auto;
                }}

            </style>
        </head>

        <body>

            <!-- COVER -->
            <div class="cover-page">
                <div class="cover-inner">

                    <div class="cover-kicker">
                        A LIFE REMEMBERED
                    </div>

                    <h1>
                        {safe(subject_name)}
                    </h1>

                    {
                        f'''
                        <div class="cover-years">
                            {safe(years)}
                        </div>
                        '''
                        if years
                        else ""
                    }

                    <div class="cover-rule"></div>

                    <div class="cover-description">
                        {safe(description)}
                    </div>

                    <div class="cover-footer">
                        MEMORIES · VOICES · MOMENTS
                    </div>

                </div>
            </div>


            <!-- TABLE OF CONTENTS -->
            <div class="section-page">

                <div class="decorative-top-rule"></div>

                <div class="section-heading">
                    Contents
                </div>

                <div class="section-subtitle">
                    A collection of moments remembered by the people
                    who shared this life.
                </div>

                <div class="memory-label">
                    WRITTEN MEMORIES
                </div>

                {toc_items}

                {
                    f'''
                    <div class="memory-divider"></div>

                    <div class="memory-label">
                        OTHER MEMORIES
                    </div>

                    <div class="toc-item">
                        Voice Memories
                    </div>

                    <div class="toc-item">
                        Media Memories
                    </div>
                    '''
                    if voice_memory_pages or media_memory_pages
                    else ""
                }

            </div>


            <!-- WRITTEN MEMORIES -->
            {written_memory_pages}


            <!-- VOICE MEMORIES -->
            {voice_memory_pages}


            <!-- MEDIA MEMORIES -->
            {media_memory_pages}


            <!-- ENDING -->
            <div class="ending-page">

                <div class="ending-inner">

                    <div class="ending-kicker">
                        THE STORY CONTINUES
                    </div>

                    <div class="ending-title">
                        The Story Continues
                    </div>

                    <div class="ending-rule"></div>

                    <div class="ending-name">
                        {safe(subject_name)}
                    </div>

                    {
                        f'''
                        <div class="ending-years">
                            {safe(years)}
                        </div>
                        '''
                        if years
                        else ""
                    }

                    <div class="ending-message">
                        Every memory carries a piece of a life.
                        Every voice keeps a moment close.
                        And every story continues through the people
                        who remember.
                    </div>

                </div>

            </div>

        </body>
        </html>
        """