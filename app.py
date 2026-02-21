#!/usr/bin/env python3
"""
TKD Cloud Annotation Dashboard - Mobile-First
Lightweight Streamlit app for remote annotation by Coach Mehdi & analysts.
Deployed to Azure App Service (Free F1).

Run locally: streamlit run dashboard_cloud/app.py
"""

import sys
import json
import streamlit as st
from pathlib import Path
from PIL import Image

# Add dashboard_cloud to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from constants import (
    TECHNIQUE_CLASSES, TECHNIQUE_DISPLAY_NAMES, TECHNIQUE_GROUPS,
    SPINNING_TECHNIQUES, WT_SCORING, DIMENSION_OPTIONS, FIGHTER_COLORS,
    TECHNIQUE_NAMES_REVERSE,
)
import data_manager

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="TKD Annotate",
    page_icon="\U0001f94b",
    layout="centered",  # centered = better on mobile than wide
    initial_sidebar_state="collapsed",  # hide sidebar on mobile by default
)

# ---------------------------------------------------------------------------
# Mobile-first CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ── Global mobile tweaks ── */
    .stApp { max-width: 600px; margin: 0 auto; }
    .block-container { padding: 0.5rem 1rem !important; }

    /* ── Large tap targets ── */
    .stButton > button {
        min-height: 48px !important;
        font-size: 1rem !important;
        border-radius: 10px !important;
    }

    /* ── Confirm button (green, full width) ── */
    .confirm-btn > div > button {
        background: #235036 !important;
        color: white !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        min-height: 56px !important;
        border: none !important;
    }
    .confirm-btn > div > button:hover {
        background: #1a3d25 !important;
    }

    /* ── Delete button (red) ── */
    .delete-btn > div > button {
        background: #dc3545 !important;
        color: white !important;
        border: none !important;
    }

    /* ── Skip button (gray) ── */
    .skip-btn > div > button {
        background: #6c757d !important;
        color: white !important;
        border: none !important;
    }

    /* ── Fighter color badges ── */
    .fighter-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 8px;
    }
    .fighter-red { background: rgba(220,53,69,0.15); color: #dc3545; border: 2px solid #dc3545; }
    .fighter-blue { background: rgba(0,119,182,0.15); color: #0077B6; border: 2px solid #0077B6; }

    /* ── Event card ── */
    .event-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 12px;
        margin: 8px 0;
        border-left: 4px solid #235036;
    }

    /* ── Progress bar ── */
    .progress-bar {
        background: #e9ecef;
        border-radius: 8px;
        height: 8px;
        margin: 4px 0 12px 0;
        overflow: hidden;
    }
    .progress-fill {
        background: linear-gradient(90deg, #235036, #69c399);
        height: 100%;
        border-radius: 8px;
        transition: width 0.3s ease;
    }

    /* ── Technique pill buttons ── */
    .tech-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: 8px 0;
    }

    /* ── AI prediction badge ── */
    .ai-badge {
        background: rgba(35,80,54,0.1);
        border: 1px solid #235036;
        border-radius: 8px;
        padding: 8px 12px;
        margin: 8px 0;
        font-size: 0.9rem;
    }

    /* ── Section headers ── */
    .section-label {
        font-size: 0.8rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 12px 0 4px 0;
        font-weight: 600;
    }

    /* ── Hide Streamlit chrome on mobile ── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* ── Compact pills/segmented control ── */
    div[data-testid="stSegmentedControl"] button {
        min-height: 44px !important;
        font-size: 0.95rem !important;
    }

    /* ── Technique category grid ── */
    .tech-category {
        font-size: 0.7rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 8px 0 2px 0;
        font-weight: 600;
    }

    /* ── Keyboard hint ── */
    .kbd-hint {
        font-size: 0.7rem;
        color: #aaa;
        text-align: center;
        margin-top: 4px;
    }
    .kbd-hint kbd {
        background: #e9ecef;
        border: 1px solid #ccc;
        border-radius: 3px;
        padding: 1px 5px;
        font-family: monospace;
        font-size: 0.7rem;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Keyboard shortcuts (C=Confirm, S=Skip, D=Delete, W=Prev, E=Next)
# ---------------------------------------------------------------------------
def inject_keyboard_shortcuts():
    """Add keyboard shortcuts for rapid annotation."""
    st.markdown("""
    <script>
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        const key = e.key.toLowerCase();
        const buttons = document.querySelectorAll('button[kind="primary"], button');
        function clickButton(text) {
            for (const btn of buttons) {
                if (btn.textContent.trim().includes(text)) {
                    btn.click();
                    e.preventDefault();
                    return true;
                }
            }
            return false;
        }
        if (key === 'c') clickButton('CONFIRM');
        else if (key === 's') clickButton('Skip');
        else if (key === 'd') clickButton('Delete');
        else if (key === 'w' || key === 'arrowleft') clickButton('Prev');
        else if (key === 'e' || key === 'arrowright') clickButton('Next');
    });
    </script>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
def init_state():
    defaults = {
        "annotator_name": "",
        "video_stem": "",
        "event_idx": 0,
        "events": [],
        "page": "select",  # select | annotate | progress
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ---------------------------------------------------------------------------
# Header with logo
# ---------------------------------------------------------------------------
import base64

@st.cache_data
def _load_logo_b64():
    logo_path = Path(__file__).parent / "logo.png"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return None

def render_header():
    logo_b64 = _load_logo_b64()
    logo_html = ""
    if logo_b64:
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height: 40px; margin-right: 10px; vertical-align: middle;">'
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #235036 0%, #18342a 100%);
         padding: 12px 16px; border-radius: 10px; margin-bottom: 12px; text-align: center;
         border-bottom: 3px solid #ebce83;">
        <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
            {logo_html}
            <div>
                <h2 style="color: white; margin: 0; font-size: 1.3rem;">TKD Match Annotation</h2>
                <p style="color: #ebce83; margin: 2px 0 0 0; font-size: 0.85rem;">Team Saudi Performance Analysis</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page: Select video + annotator
# ---------------------------------------------------------------------------
def page_select():
    render_header()

    # Annotator — load persisted list
    st.markdown('<p class="section-label">Who is annotating?</p>', unsafe_allow_html=True)
    _annotators_file = data_manager.ANNOTATIONS_DIR / "annotators.json"
    _default_annotators = ["Coach Mehdi", "Luke", "Analyst"]
    if _annotators_file.exists():
        try:
            _saved = json.loads(_annotators_file.read_text(encoding="utf-8"))
            annotator_options = list(dict.fromkeys(_default_annotators + _saved))
        except Exception:
            annotator_options = _default_annotators[:]
    else:
        annotator_options = _default_annotators[:]

    selected = st.pills("annotator", annotator_options, label_visibility="collapsed")
    if selected:
        st.session_state["annotator_name"] = selected

    # Add new annotator
    with st.expander("+ Add annotator"):
        _new_name = st.text_input("Name", placeholder="Enter new annotator name", key="cloud_new_annotator")
        if _new_name and _new_name.strip():
            _new_name = _new_name.strip()
            if st.button("Add", key="cloud_add_annotator"):
                if _new_name not in annotator_options:
                    annotator_options.append(_new_name)
                    _annotators_file.parent.mkdir(parents=True, exist_ok=True)
                    _annotators_file.write_text(
                        json.dumps(annotator_options, indent=2), encoding="utf-8"
                    )
                st.session_state["annotator_name"] = _new_name
                st.rerun()

    st.markdown("---")

    # Video selection
    videos = data_manager.list_videos()
    if not videos:
        st.warning("No analysed videos found. Run analysis locally first, then push results.")
        st.markdown("""
        **Setup steps:**
        1. Analyse a video locally: `python scripts/analyze_video.py --video match.mp4`
        2. Extract thumbnails: `python scripts/extract_thumbnails.py --video match.mp4`
        3. Push `data/results/` and `data/thumbnails/` to the GitHub repo
        """)
        return

    # ── Auto-group videos by match ──
    import re

    def _parse_match(stem):
        """Extract base match name and part number from filename."""
        # Pattern: ends with _1, _2, etc. or (1), (2)
        m = re.match(r'^(.+?)[\s_]*\((\d+)\)$', stem)
        if m:
            return m.group(1).strip(), int(m.group(2))
        m = re.match(r'^(.+?)_(\d+)$', stem)
        if m:
            return m.group(1).strip(), int(m.group(2))
        return stem, 1

    def _clean_name(base):
        """Make a readable display name from the base filename."""
        name = base
        # Remove date prefix like 20251116-
        name = re.sub(r'^\d{8}-', '', name)
        # Remove "Taekwondo_" prefix
        name = re.sub(r'^Taekwondo_', '', name)
        # Replace underscores with spaces
        name = name.replace('_', ' ')
        # Clean up multiple spaces
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    # Group videos: {base_name: [(stem, part_num), ...]}
    match_groups = {}
    for v in videos:
        base, part = _parse_match(v)
        if base not in match_groups:
            match_groups[base] = []
        match_groups[base].append((v, part))

    # Sort parts within each group
    for base in match_groups:
        match_groups[base].sort(key=lambda x: x[1])

    # ── Match selector ──
    st.markdown('<p class="section-label">Select match</p>', unsafe_allow_html=True)
    base_names = list(match_groups.keys())
    display_names = [_clean_name(b) for b in base_names]
    selected_idx = st.selectbox(
        "match_select", options=range(len(base_names)),
        format_func=lambda i: display_names[i],
        key="match_selector", label_visibility="collapsed",
    )
    selected_base = base_names[selected_idx]
    parts = match_groups[selected_base]

    # Load existing match data
    match_name = st.session_state.get("match_name", "") or _clean_name(selected_base)
    mdata = data_manager.load_matches().get(match_name, {})
    if mdata.get("red_name") and not st.session_state.get("red_fighter_name"):
        st.session_state["red_fighter_name"] = mdata["red_name"]
    if mdata.get("blue_name") and not st.session_state.get("blue_fighter_name"):
        st.session_state["blue_fighter_name"] = mdata["blue_name"]

    # ── Match details (editable) ──
    with st.expander("Match Details", expanded=len(parts) > 1):
        match_name = st.text_input(
            "Match name", value=match_name,
            placeholder="e.g. Dunya vs CHN - Semi Final",
            key="sel_match_name",
        )
        st.session_state["match_name"] = match_name

        fc1, fc2 = st.columns(2)
        with fc1:
            red_name = st.text_input(
                "RED (Hong)",
                value=st.session_state.get("red_fighter_name", ""),
                placeholder="e.g. Dunya",
                key="sel_red_name",
            )
            st.session_state["red_fighter_name"] = red_name
        with fc2:
            blue_name = st.text_input(
                "BLUE (Chung)",
                value=st.session_state.get("blue_fighter_name", ""),
                placeholder="e.g. Opponent",
                key="sel_blue_name",
            )
            st.session_state["blue_fighter_name"] = blue_name

        if len(parts) > 1:
            st.success(f"{len(parts)} parts auto-grouped for this match")

    # Start time filter
    st.markdown('<p class="section-label">Skip start (seconds)</p>', unsafe_allow_html=True)
    start_sec = st.slider("start_filter", 0, 120, 0, 5,
                          label_visibility="collapsed",
                          help="Skip events before this time (walkouts, ceremonies)")

    # ── Parts list ──
    st.markdown('<p class="section-label">Parts</p>', unsafe_allow_html=True)

    for video_stem, part_num in parts:
        techniques = data_manager.load_techniques(video_stem)
        if start_sec > 0:
            techniques = [e for e in techniques if e.get("start_timestamp", 0) >= start_sec]
        stats = data_manager.get_annotation_stats(video_stem, len(techniques))

        col1, col2 = st.columns([4, 1])
        with col1:
            part_label = f"Part {part_num}" if len(parts) > 1 else "Full match"
            st.markdown(f"**{part_label}**")
            st.markdown(f"<div class='progress-bar'>"
                       f"<div class='progress-fill' style='width:{stats['progress_pct']}%'></div>"
                       f"</div>", unsafe_allow_html=True)
            st.caption(f"{stats['annotated']}/{stats['total_events']} events "
                      f"({stats['progress_pct']}%)")
        with col2:
            if st.button("Open", key=f"open_{video_stem}", use_container_width=True):
                if not st.session_state["annotator_name"]:
                    st.error("Please select or enter your name first")
                else:
                    # Save match group
                    if match_name:
                        data_manager.save_match_group(
                            match_name, video_stem, part_num,
                            red_name=red_name, blue_name=blue_name,
                        )
                    st.session_state["video_stem"] = video_stem
                    st.session_state["video_part"] = part_num
                    st.session_state["events"] = techniques
                    st.session_state["start_sec"] = start_sec
                    st.session_state["event_idx"] = _find_next_unannotated(video_stem, techniques)
                    st.session_state["page"] = "annotate"
                    st.rerun()


    # ── Upload saved annotations (restore after restart) ──
    st.markdown("---")
    with st.expander("Upload / Restore Annotations"):
        st.caption("Streamlit Cloud resets files on restart. Upload your saved JSON to restore.")
        uploaded = st.file_uploader(
            "Upload annotations JSON", type=["json"],
            accept_multiple_files=True, label_visibility="collapsed",
        )
        if uploaded:
            for uf in uploaded:
                try:
                    ann_data = json.load(uf)
                    # Derive video_stem from filename: {stem}_annotations.json
                    stem = uf.name.replace("_annotations.json", "").replace(".json", "")
                    data_manager.save_annotations(stem, ann_data)
                    st.success(f"Restored {len(ann_data.get('annotations', []))} annotations for {stem}")
                except Exception as e:
                    st.error(f"Failed to load {uf.name}: {e}")

        # Also allow uploading match groups
        match_file = st.file_uploader(
            "Upload match groups JSON", type=["json"],
            key="match_upload", label_visibility="collapsed",
        )
        if match_file:
            try:
                matches = json.load(match_file)
                data_manager.save_matches(matches)
                st.success(f"Restored {len(matches)} match groups")
            except Exception as e:
                st.error(f"Failed to load match groups: {e}")


def _find_next_unannotated(video_stem: str, events: list) -> int:
    """Find the index of the first unannotated event."""
    for i, evt in enumerate(events):
        existing = data_manager.get_annotation_for_event(
            video_stem, evt["start_frame"], evt["end_frame"],
            evt.get("fighter_color", "unknown")
        )
        if not existing:
            return i
    return 0


# ---------------------------------------------------------------------------
# Page: Annotate events
# ---------------------------------------------------------------------------
def page_annotate():
    video_stem = st.session_state["video_stem"]
    events = st.session_state["events"]
    idx = st.session_state["event_idx"]

    if not events:
        st.warning("No events found for this video.")
        if st.button("Back"):
            st.session_state["page"] = "select"
            st.rerun()
        return

    total = len(events)

    # ── Build annotation status for all events (once per render) ──
    ann_data_all = data_manager.load_annotations(video_stem)
    _ann_keys = set()
    for ann in ann_data_all.get("annotations", []):
        _ann_keys.add((ann.get("start_frame"), ann.get("end_frame"), ann.get("fighter_color")))

    def _is_annotated(evt):
        return (evt.get("start_frame"), evt.get("end_frame"),
                evt.get("fighter_color", "unknown")) in _ann_keys

    # ── Top bar: back + progress + annotator ──
    top1, top2, top3 = st.columns([1, 2, 1])
    with top1:
        if st.button("\u2190 Back", use_container_width=True):
            st.session_state["page"] = "select"
            st.rerun()
    with top2:
        n_done = sum(1 for e in events if _is_annotated(e))
        n_todo = total - n_done
        st.markdown(f"<div style='text-align:center; font-weight:600;'>"
                   f"{n_done}/{total} done</div>",
                   unsafe_allow_html=True)
        pct = round(n_done / max(1, total) * 100, 1)
        st.markdown(f"<div class='progress-bar'>"
                   f"<div class='progress-fill' style='width:{pct}%'></div>"
                   f"</div>", unsafe_allow_html=True)
    with top3:
        st.markdown(f"<div style='text-align:right; font-size:0.8rem; color:#6c757d;'>"
                   f"{st.session_state['annotator_name']}</div>",
                   unsafe_allow_html=True)

    # ── Editable match details (fix mistakes) ──
    match_info = data_manager.get_match_for_video(video_stem)
    with st.expander("Match Details", expanded=False):
        md1, md2 = st.columns(2)
        with md1:
            red_edit = st.text_input(
                "RED fighter", value=st.session_state.get("red_fighter_name", ""),
                key="edit_red_name",
            )
            st.session_state["red_fighter_name"] = red_edit
        with md2:
            blue_edit = st.text_input(
                "BLUE fighter", value=st.session_state.get("blue_fighter_name", ""),
                key="edit_blue_name",
            )
            st.session_state["blue_fighter_name"] = blue_edit

        md3, md4 = st.columns(2)
        with md3:
            match_edit = st.text_input(
                "Match name", value=st.session_state.get("match_name", ""),
                key="edit_match_name",
            )
            st.session_state["match_name"] = match_edit
        with md4:
            part_edit = st.selectbox(
                "Part", options=[1, 2, 3, 4, 5],
                index=st.session_state.get("video_part", 1) - 1,
                key="edit_video_part",
            )
            st.session_state["video_part"] = part_edit

        if st.button("Save match details", use_container_width=True):
            if match_edit:
                data_manager.save_match_group(
                    match_edit, video_stem, part_edit,
                    red_name=red_edit, blue_name=blue_edit,
                )
                st.success("Match details saved")

    # ── Filter: All / To Do / Done ──
    filt = st.segmented_control(
        "event_filter",
        options=["All", f"To Do ({n_todo})", f"Done ({n_done})"],
        default=st.session_state.get("event_filter", "All"),
        label_visibility="collapsed",
    )
    st.session_state["event_filter"] = filt or "All"

    # Build filtered index list
    if filt and filt.startswith("To Do"):
        filtered_indices = [i for i, e in enumerate(events) if not _is_annotated(e)]
    elif filt and filt.startswith("Done"):
        filtered_indices = [i for i, e in enumerate(events) if _is_annotated(e)]
    else:
        filtered_indices = list(range(total))

    # Clamp idx to filtered set
    if filtered_indices:
        if idx not in filtered_indices:
            # Jump to nearest filtered event
            idx = min(filtered_indices, key=lambda i: abs(i - idx))
            st.session_state["event_idx"] = idx
    else:
        st.info("No events match this filter.")
        return

    event = events[idx]
    pos_in_filter = filtered_indices.index(idx)
    filter_total = len(filtered_indices)

    # ── Navigation (respects filter) ──
    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button("\u25c0 Prev", disabled=(pos_in_filter == 0), use_container_width=True):
            st.session_state["event_idx"] = filtered_indices[pos_in_filter - 1]
            st.rerun()
    with nav2:
        # Status badge
        if _is_annotated(event):
            badge = '<span style="background:#d4edda; color:#155724; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:600;">DONE</span>'
        else:
            badge = '<span style="background:#fff3cd; color:#856404; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:600;">TO DO</span>'
        st.markdown(f"<div style='text-align:center; font-size:1.1rem; font-weight:700; "
                   f"padding:4px 0;'>Event {pos_in_filter + 1} / {filter_total}</div>"
                   f"<div style='text-align:center;'>{badge}</div>",
                   unsafe_allow_html=True)
    with nav3:
        if st.button("Next \u25b6", disabled=(pos_in_filter >= filter_total - 1), use_container_width=True):
            st.session_state["event_idx"] = filtered_indices[pos_in_filter + 1]
            st.rerun()

    st.markdown("---")

    # ── Thumbnail with skeleton overlay ──
    start_frame = event.get("start_frame", 0)
    thumb_path = data_manager.get_thumbnail_path(video_stem, start_frame)
    if thumb_path:
        img = Image.open(thumb_path)
        st.image(img, use_container_width=True,
                 caption=f"Frame {start_frame} (skeleton + target zones)")
    else:
        st.markdown(
            f"<div style='background:#e9ecef; padding:40px; text-align:center; "
            f"border-radius:8px; color:#6c757d;'>"
            f"No thumbnail<br>Frame {event.get('start_frame', '?')}-{event.get('end_frame', '?')}"
            f"</div>", unsafe_allow_html=True
        )

    # ── Box assignments (numbered detections on the thumbnail) ──
    box_meta = data_manager.get_box_metadata(video_stem, start_frame)
    if box_meta:
        _color_options = ["red", "blue", "referee", "unknown"]
        _color_labels = {
            "red": "RED", "blue": "BLUE",
            "referee": "REF", "unknown": "?",
        }
        _color_dots = {
            "red": "#dc3545", "blue": "#0077B6",
            "referee": "#6c757d", "unknown": "#ccc",
        }

        st.markdown('<p class="section-label">Box Assignments</p>', unsafe_allow_html=True)
        box_cols = st.columns(len(box_meta))
        for i, bm in enumerate(box_meta):
            box_num = bm["box"]
            auto_color = bm.get("auto_color", "unknown")
            with box_cols[i]:
                dot = _color_dots.get(auto_color, "#ccc")
                st.markdown(
                    f'<div style="text-align:center; font-weight:700; font-size:1.1rem; '
                    f'color:{dot}; border:2px solid {dot}; border-radius:8px; padding:4px; '
                    f'margin-bottom:4px;">Box {box_num}</div>',
                    unsafe_allow_html=True,
                )
                new_color = st.selectbox(
                    f"box_{box_num}",
                    options=_color_options,
                    index=_color_options.index(auto_color) if auto_color in _color_options else 3,
                    format_func=lambda x: _color_labels.get(x, x),
                    key=f"box_assign_{idx}_{box_num}",
                    label_visibility="collapsed",
                )
                # Store reassignment in session state
                if new_color != auto_color:
                    st.session_state[f"box_override_{idx}_{box_num}"] = new_color

    # ── Event metadata ──
    fighter = event.get("fighter_color", "unknown")
    ai_tech = event.get("technique", "neutral_stance")
    ai_display = TECHNIQUE_DISPLAY_NAMES.get(ai_tech, ai_tech)
    confidence = event.get("confidence", 0)
    timestamp = event.get("start_timestamp", 0)
    mins = int(timestamp // 60)
    secs = int(timestamp % 60)

    red_name = st.session_state.get("red_fighter_name", "")
    blue_name = st.session_state.get("blue_fighter_name", "")
    red_label = red_name or "RED"
    blue_label = blue_name or "BLUE"

    # Lookup existing annotations for both fighters at this frame
    def _find_existing(color):
        key = (event["start_frame"], event["end_frame"], color)
        if key in _ann_keys:
            for _a in ann_data_all.get("annotations", []):
                if (_a.get("start_frame"), _a.get("end_frame"), _a.get("fighter_color")) == key:
                    return _a
        return None

    existing_red = _find_existing("red")
    existing_blue = _find_existing("blue")

    # AI badge + timestamp + dismiss
    ai_col1, ai_col2 = st.columns([5, 1])
    with ai_col1:
        st.markdown(f"""
        <div class="ai-badge">
            AI: <strong>{ai_display}</strong>
            &nbsp;&middot;&nbsp; {confidence:.0%}
            &nbsp;&middot;&nbsp; {fighter.upper()}
            &nbsp;&middot;&nbsp; {mins}:{secs:02d}
        </div>
        """, unsafe_allow_html=True)
    with ai_col2:
        if st.button("X", key=f"dismiss_ai_{idx}", help="Dismiss AI prediction (false positive)"):
            # Mark as false positive — skip to next event
            data_manager.add_annotation(
                video_stem=video_stem,
                event=event,
                corrections={
                    "technique": "neutral_stance",
                    "fighter_color": fighter,
                    "notes": "Dismissed as false positive",
                },
                annotated_by=st.session_state.get("annotator_name", ""),
            )
            # Move to next
            st.session_state["event_idx"] = min(idx + 1, len(events) - 1)
            st.rerun()

    # ── Scoreboard (source of truth) ──
    sb_key = f"sb_{video_stem}"
    if sb_key not in st.session_state:
        st.session_state[sb_key] = {"red": 0, "blue": 0, "round": "R1"}

    sb1, sb_vs, sb2 = st.columns([3, 1, 3])
    with sb1:
        sb_red = st.number_input(
            red_label, min_value=0, max_value=99, step=1,
            value=st.session_state[sb_key]["red"], key=f"sb_red_{idx}",
        )
        st.session_state[sb_key]["red"] = sb_red
    with sb_vs:
        st.markdown('<div style="text-align:center; padding:24px 0; font-weight:700; '
                    'color:#6c757d; font-size:1.1rem;">vs</div>', unsafe_allow_html=True)
    with sb2:
        sb_blue = st.number_input(
            blue_label, min_value=0, max_value=99, step=1,
            value=st.session_state[sb_key]["blue"], key=f"sb_blue_{idx}",
        )
        st.session_state[sb_key]["blue"] = sb_blue

    sb_round = st.segmented_control(
        "round", options=["R1", "R2", "R3", "GR"],
        default=st.session_state[sb_key].get("round", "R1"),
        label_visibility="visible",
    )
    if sb_round:
        st.session_state[sb_key]["round"] = sb_round

    # ── Relationship rules (from PDF) ──
    # Role mirror: if one fighter attacks, the other defends/counters
    _ROLE_MIRROR = {
        "Attack": "Contre Attack",
        "Contre Attack": "Attack",
        "Defence": "Attack",
    }
    # Attitude mirror: forward attacker → backward defender (suggestion only)
    _ATTITUDE_MIRROR = {
        "Forward": "Backward",
        "Backward": "Forward",
        "Stationary": "Stationary",
    }

    def _penalty_pts(penalty_str):
        """Extract point value from penalty string."""
        if not penalty_str or penalty_str == "None":
            return 0
        if "(-2)" in penalty_str or "(+2)" in penalty_str:
            return 2
        if "(-1)" in penalty_str or "(+1)" in penalty_str:
            return 1
        return 0

    # ── RED | BLUE tabs — each with all 9 layers (from PDF) ──
    # Read the OTHER fighter's role from previous render (session state)
    # so we can auto-suggest linked defaults
    def _get_other_role(prefix):
        """Get the other fighter's role from session state (previous render)."""
        other = "blue" if prefix == "red" else "red"
        return st.session_state.get(f"{other}_role_{idx}")

    def _get_other_attitude(prefix):
        other = "blue" if prefix == "red" else "red"
        return st.session_state.get(f"{other}_attitude_{idx}")

    def _get_other_penalty(prefix):
        other = "blue" if prefix == "red" else "red"
        return st.session_state.get(f"{other}_penalty_{idx}")

    def _render_fighter_layers(color, color_hex, color_bg, label, existing_ann, is_active):
        """Render all 9 annotation layers for one fighter.
        Returns dict of selected values.
        """
        prefix = color  # "red" or "blue"
        src = existing_ann if existing_ann else (event if is_active else {})

        # Status badge
        if existing_ann:
            prev_tech = TECHNIQUE_DISPLAY_NAMES.get(existing_ann.get("technique", ""), "?")
            st.markdown(
                f'<div style="background:{color_bg}; border:1px solid {color_hex}; '
                f'border-radius:8px; padding:6px 10px; font-size:0.8rem; margin-bottom:8px;">'
                f'Previously: <strong>{prev_tech}</strong> '
                f'by {existing_ann.get("annotated_by", "?")}</div>',
                unsafe_allow_html=True,
            )

        if not is_active:
            st.caption("(Reaction — what were they doing?)")

        # Layer 1: Attitude — linked: mirror of other fighter's attitude
        attitude_default = _match_option(src.get("attitude"), DIMENSION_OPTIONS["attitude"])
        if not attitude_default and not is_active:
            other_att = _get_other_attitude(prefix)
            if other_att:
                attitude_default = _ATTITUDE_MIRROR.get(other_att)
        attitude = st.segmented_control(
            "attitude", options=DIMENSION_OPTIONS["attitude"],
            default=attitude_default,
            label_visibility="visible", key=f"{prefix}_attitude_{idx}",
        )

        # Layer 2: Stance
        stance = st.segmented_control(
            "stance", options=DIMENSION_OPTIONS["guard_stance"],
            default=_match_option(src.get("guard_stance"), DIMENSION_OPTIONS["guard_stance"]),
            label_visibility="visible", key=f"{prefix}_stance_{idx}",
        )

        # Layer 3: Role — linked: mirror of other fighter's role
        role_default = _match_option(src.get("role"), DIMENSION_OPTIONS["role"])
        if not role_default and not is_active:
            other_role = _get_other_role(prefix)
            if other_role:
                role_default = _ROLE_MIRROR.get(other_role)
        role = st.segmented_control(
            "role", options=DIMENSION_OPTIONS["role"],
            default=role_default,
            label_visibility="visible", key=f"{prefix}_role_{idx}",
        )

        # Layer 4: Type
        action_type = st.segmented_control(
            "type", options=DIMENSION_OPTIONS["action_type"],
            default=_match_option(src.get("action_type"), DIMENSION_OPTIONS["action_type"]),
            label_visibility="visible", key=f"{prefix}_type_{idx}",
        )

        # Layer 5: Leg
        leg = st.segmented_control(
            "leg", options=DIMENSION_OPTIONS["leg_used"],
            default=_match_option(src.get("leg_used", src.get("kicking_leg")),
                                  DIMENSION_OPTIONS["leg_used"]),
            label_visibility="visible", key=f"{prefix}_leg_{idx}",
        )

        # Layer 6: Technique (pills per category)
        st.markdown('<p class="section-label">Technique</p>', unsafe_allow_html=True)
        default_tech = (existing_ann or {}).get("technique") or (ai_tech if is_active else None)
        current_sel = st.session_state.get(f"sel_tech_{prefix}_{idx}", default_tech)

        tech_sel = None
        for cat_name, cat_techs in TECHNIQUE_GROUPS.items():
            st.markdown(f'<p class="tech-category">{cat_name}</p>', unsafe_allow_html=True)
            cat_default = current_sel if current_sel in cat_techs else None
            picked = st.pills(
                f"tech_{cat_name}",
                options=cat_techs,
                format_func=lambda x: TECHNIQUE_DISPLAY_NAMES.get(x, x),
                default=cat_default,
                label_visibility="collapsed",
                key=f"pills_{prefix}_{idx}_{cat_name}",
            )
            if picked:
                tech_sel = picked

        if not tech_sel:
            tech_sel = default_tech
        st.session_state[f"sel_tech_{prefix}_{idx}"] = tech_sel

        # Layer 7: Target
        target = st.segmented_control(
            "target", options=DIMENSION_OPTIONS["target_zone"],
            default=_match_option(
                src.get("target_zone"), DIMENSION_OPTIONS["target_zone"]),
            label_visibility="visible", key=f"{prefix}_target_{idx}",
        )

        # Layer 8: Value — linked: other's penalty gives this fighter points
        value_default = _match_option(src.get("scoring_value"), DIMENSION_OPTIONS["scoring_value"])
        other_pen = _get_other_penalty(prefix)
        other_pen_pts = _penalty_pts(other_pen)
        if other_pen_pts > 0 and not value_default:
            value_default = str(other_pen_pts)
            st.info(f"Opponent penalty → +{other_pen_pts} pts")

        scoring = st.segmented_control(
            "value", options=["No score", "1", "2", "3", "4", "6"],
            default=value_default,
            label_visibility="visible", key=f"{prefix}_value_{idx}",
        )

        # Layer 9: Penalty
        penalty = st.selectbox(
            "Penalty", options=DIMENSION_OPTIONS["penalty"],
            index=0, key=f"{prefix}_penalty_{idx}",
        )

        # Coach notes
        notes = st.text_area(
            "Notes", value=src.get("notes", ""),
            placeholder="Coach observations...",
            height=68, key=f"{prefix}_notes_{idx}",
        )

        return {
            "fighter_color": color,
            "attitude": attitude,
            "guard_stance": stance,
            "role": role,
            "action_type": action_type,
            "leg_used": leg,
            "technique": tech_sel,
            "target_zone": (target or "Body").lower().replace("body", "trunk"),
            "scoring_value": scoring,
            "penalty": penalty if (penalty and penalty != "None") else None,
            "notes": notes,
        }

    # Render tabs
    red_tab_label = f"RED {red_label}"
    blue_tab_label = f"BLUE {blue_label}"
    if fighter == "red":
        red_tab_label += " *"
    elif fighter == "blue":
        blue_tab_label += " *"

    tab_red, tab_blue = st.tabs([red_tab_label, blue_tab_label])
    with tab_red:
        red_data = _render_fighter_layers(
            "red", "#dc3545", "rgba(220,53,69,0.12)", red_label,
            existing_red, is_active=(fighter == "red"))
    with tab_blue:
        blue_data = _render_fighter_layers(
            "blue", "#0077B6", "rgba(0,119,182,0.12)", blue_label,
            existing_blue, is_active=(fighter == "blue"))

    # ── Relationship summary (visible after both tabs) ──
    links = []
    r_role = red_data.get("role")
    b_role = blue_data.get("role")
    if r_role and b_role:
        expected = _ROLE_MIRROR.get(r_role)
        if expected and b_role == expected:
            links.append(f'<span style="color:#155724;">RED {r_role} ↔ BLUE {b_role}</span>')
        elif expected and b_role != expected:
            links.append(
                f'<span style="color:#856404;">RED {r_role} ↔ BLUE {b_role} '
                f'(expected {expected}?)</span>')

    r_pen_pts = _penalty_pts(red_data.get("penalty"))
    b_pen_pts = _penalty_pts(blue_data.get("penalty"))
    if r_pen_pts > 0:
        links.append(f'<span style="color:#dc3545;">RED penalty → BLUE +{r_pen_pts}</span>')
    if b_pen_pts > 0:
        links.append(f'<span style="color:#0077B6;">BLUE penalty → RED +{b_pen_pts}</span>')

    if links:
        st.markdown(
            f'<div style="background:#f0f7f4; border:1px solid #c3d9d1; border-radius:8px; '
            f'padding:8px 12px; font-size:0.8rem; margin:6px 0;">'
            f'<strong>Links:</strong> {"&nbsp;&middot;&nbsp;".join(links)}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Filmstrip (scrollable + zoom) ──
    strip_path = data_manager.THUMBNAILS_DIR / video_stem / "strips" / f"strip_{start_frame:06d}.jpg"
    if strip_path.exists():
        fs_col1, fs_col2 = st.columns([3, 1])
        with fs_col1:
            st.markdown('<p class="section-label">Filmstrip</p>', unsafe_allow_html=True)
        with fs_col2:
            zoomed = st.checkbox("Zoom", value=False, key=f"strip_zoom_{idx}")
        import base64
        with open(strip_path, "rb") as sf:
            strip_b64 = base64.b64encode(sf.read()).decode()
        sf_start = event.get('start_frame', '?')
        sf_end = event.get('end_frame', '?')
        strip_height = "200px" if zoomed else "80px"
        st.markdown(f"""
        <div style="overflow-x:auto; -webkit-overflow-scrolling:touch;
             border:1px solid #e0e0e0; border-radius:8px; padding:4px;
             margin:4px 0; white-space:nowrap;">
            <img src="data:image/jpeg;base64,{strip_b64}"
                 style="height:{strip_height}; max-width:none; display:block;">
        </div>
        <p style="font-size:0.7rem; color:#999; text-align:center; margin:2px 0;">
            Frames {sf_start} - {sf_end}
        </p>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Action buttons ──
    st.markdown('<div class="confirm-btn">', unsafe_allow_html=True)
    if st.button("\u2713  CONFIRM BOTH  (C)", use_container_width=True, type="primary"):
        # Save both fighters' annotations
        for fdata in [red_data, blue_data]:
            if fdata.get("technique") or fdata.get("role") or fdata.get("attitude"):
                corrections = {
                    **fdata,
                    "scoreboard_red": st.session_state[sb_key]["red"],
                    "scoreboard_blue": st.session_state[sb_key]["blue"],
                    "scoreboard_round": st.session_state[sb_key].get("round", "R1"),
                    "match_name": st.session_state.get("match_name", ""),
                    "video_part": st.session_state.get("video_part", 1),
                }
                # Build event copy with correct fighter_color
                evt_copy = {**event, "fighter_color": fdata["fighter_color"]}
                data_manager.add_annotation(
                    video_stem, evt_copy, corrections,
                    annotated_by=st.session_state["annotator_name"]
                )
        # Auto-advance to next filtered event
        if pos_in_filter < filter_total - 1:
            st.session_state["event_idx"] = filtered_indices[pos_in_filter + 1]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Skip + Delete + Progress row
    btn1, btn2, btn3 = st.columns(3)
    with btn1:
        st.markdown('<div class="skip-btn">', unsafe_allow_html=True)
        if st.button("Skip (S)", use_container_width=True):
            if pos_in_filter < filter_total - 1:
                st.session_state["event_idx"] = filtered_indices[pos_in_filter + 1]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with btn2:
        st.markdown('<div class="delete-btn">', unsafe_allow_html=True)
        if st.button("Delete (D)", use_container_width=True):
            data_manager.delete_annotation(
                video_stem, event["start_frame"], event["end_frame"],
                event.get("fighter_color", "unknown")
            )
            if pos_in_filter < filter_total - 1:
                st.session_state["event_idx"] = filtered_indices[pos_in_filter + 1]
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with btn3:
        if st.button("Progress", use_container_width=True):
            st.session_state["page"] = "progress"
            st.rerun()

    # Keyboard shortcuts hint
    st.markdown('<p class="kbd-hint"><kbd>C</kbd> Confirm &nbsp; '
                '<kbd>S</kbd> Skip &nbsp; <kbd>D</kbd> Delete &nbsp; '
                '<kbd>W</kbd>/<kbd>&larr;</kbd> Prev &nbsp; '
                '<kbd>E</kbd>/<kbd>&rarr;</kbd> Next</p>',
                unsafe_allow_html=True)

    # Inject keyboard shortcuts
    inject_keyboard_shortcuts()


def _match_option(value, options):
    """Match a stored value to the closest option, case-insensitive."""
    if not value:
        return None
    value_lower = str(value).lower().replace("_", " ")
    for opt in options:
        if opt.lower() == value_lower:
            return opt
    # Partial match
    for opt in options:
        if value_lower in opt.lower() or opt.lower() in value_lower:
            return opt
    return None


# ---------------------------------------------------------------------------
# Page: Progress overview
# ---------------------------------------------------------------------------
def page_progress():
    render_header()
    video_stem = st.session_state["video_stem"]
    events = st.session_state["events"]

    if st.button("\u2190 Back to annotation"):
        st.session_state["page"] = "annotate"
        st.rerun()

    if not video_stem:
        st.info("Select a video first.")
        return

    # ── Match group info ──
    match_info = data_manager.get_match_for_video(video_stem)
    if match_info:
        match_name = match_info["match_name"]
        red_fn = match_info.get("red_name", "")
        blue_fn = match_info.get("blue_name", "")
        match_videos = match_info.get("videos", [])
        part_label = f"Part {match_info['video_part']} of {len(match_videos)}"
        st.markdown(
            f'<div style="background:#f0f7f4; border:1px solid #c3d9d1; border-radius:8px; '
            f'padding:8px 12px; font-size:0.85rem; margin-bottom:8px;">'
            f'<strong>{match_name}</strong> &middot; {part_label}'
            f'{"  &middot;  " + red_fn + " vs " + blue_fn if red_fn or blue_fn else ""}'
            f'</div>', unsafe_allow_html=True,
        )
    else:
        match_videos = []

    stats = data_manager.get_annotation_stats(video_stem, len(events))

    # Progress
    st.markdown(f"### {video_stem}")
    st.markdown(f"<div class='progress-bar' style='height:12px;'>"
               f"<div class='progress-fill' style='width:{stats['progress_pct']}%'></div>"
               f"</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Annotated", stats["annotated"])
    with col2:
        st.metric("Remaining", stats["remaining"])
    with col3:
        st.metric("Progress", f"{stats['progress_pct']}%")

    # By annotator
    if stats["by_annotator"]:
        st.markdown("#### By Annotator")
        for name, count in sorted(stats["by_annotator"].items(),
                                   key=lambda x: x[1], reverse=True):
            st.markdown(f"- **{name}**: {count} annotations")

    # By technique (with per-technique progress bars)
    if stats["by_technique"]:
        st.markdown("#### By Technique")
        target_per_tech = 50  # target annotations per technique
        for tech, count in sorted(stats["by_technique"].items(),
                                   key=lambda x: x[1], reverse=True):
            display = TECHNIQUE_DISPLAY_NAMES.get(tech, tech)
            pct = min(100, round(count / target_per_tech * 100))
            bar_color = "#235036" if pct >= 100 else "#69c399" if pct >= 50 else "#ebce83"
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:8px; margin:2px 0;'>"
                f"<span style='width:100px; font-size:0.85rem;'>{display}</span>"
                f"<div style='flex:1; background:#e9ecef; border-radius:4px; height:10px;'>"
                f"<div style='width:{pct}%; background:{bar_color}; height:100%; border-radius:4px;'></div>"
                f"</div>"
                f"<span style='font-size:0.8rem; color:#6c757d; width:50px; text-align:right;'>{count}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

    # Two-column score tally (from scoreboard, not auto-calculated)
    st.markdown("---")
    st.markdown("#### Scoreboard")
    ann_data = data_manager.load_annotations(video_stem)
    red_name_disp = st.session_state.get("red_fighter_name", "") or "RED"
    blue_name_disp = st.session_state.get("blue_fighter_name", "") or "BLUE"

    # Get latest scoreboard reading from annotations (most recent entry wins)
    sb_red, sb_blue, sb_round = 0, 0, ""
    for ann in reversed(ann_data.get("annotations", [])):
        if ann.get("scoreboard_red") is not None:
            sb_red = ann["scoreboard_red"]
            sb_blue = ann.get("scoreboard_blue", 0)
            sb_round = ann.get("scoreboard_round", "")
            break

    # Also check session state for current unsaved values
    sb_key = f"sb_{video_stem}"
    if sb_key in st.session_state:
        sb_red = max(sb_red, st.session_state[sb_key].get("red", 0) or 0)
        sb_blue = max(sb_blue, st.session_state[sb_key].get("blue", 0) or 0)
        sb_round = st.session_state[sb_key].get("round", sb_round) or sb_round

    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown(f"""<div style="text-align:center; border:2px solid #dc3545;
             border-radius:10px; padding:12px; background:rgba(220,53,69,0.06);">
            <div style="font-size:0.8rem; color:#dc3545; font-weight:600;">{red_name_disp}</div>
            <div style="font-size:2rem; font-weight:700; color:#dc3545;">{sb_red}</div>
        </div>""", unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""<div style="text-align:center; border:2px solid #0077B6;
             border-radius:10px; padding:12px; background:rgba(0,119,182,0.06);">
            <div style="font-size:0.8rem; color:#0077B6; font-weight:600;">{blue_name_disp}</div>
            <div style="font-size:2rem; font-weight:700; color:#0077B6;">{sb_blue}</div>
        </div>""", unsafe_allow_html=True)
    if sb_round:
        st.markdown(f'<p style="text-align:center; font-size:0.8rem; color:#6c757d; margin:4px 0;">{sb_round}</p>',
                    unsafe_allow_html=True)

    # ── Combined match stats (across all videos in the match) ──
    if match_videos and len(match_videos) > 1:
        st.markdown("---")
        st.markdown("#### Full Match (All Parts)")
        combined_anns = []
        combined_events = 0
        for mv in match_videos:
            mv_stem = mv["video_stem"]
            mv_techs = data_manager.load_techniques(mv_stem)
            combined_events += len(mv_techs)
            mv_ann = data_manager.load_annotations(mv_stem)
            for a in mv_ann.get("annotations", []):
                a["_part"] = mv.get("part", 1)
                a["_video"] = mv_stem
            combined_anns.extend(mv_ann.get("annotations", []))

        # Combined progress
        comb_pct = round(len(combined_anns) / max(1, combined_events) * 100, 1)
        st.markdown(f"<div class='progress-bar' style='height:10px;'>"
                   f"<div class='progress-fill' style='width:{comb_pct}%'></div>"
                   f"</div>", unsafe_allow_html=True)
        st.caption(f"{len(combined_anns)}/{combined_events} events annotated ({comb_pct}%)")

        # Per-part breakdown
        for mv in match_videos:
            mv_stem = mv["video_stem"]
            part_n = mv.get("part", 1)
            n_ann = sum(1 for a in combined_anns if a.get("_video") == mv_stem)
            n_tech = len(data_manager.load_techniques(mv_stem))
            ppct = round(n_ann / max(1, n_tech) * 100)
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:8px; margin:2px 0;'>"
                f"<span style='width:80px; font-size:0.8rem; font-weight:600;'>Pt.{part_n}</span>"
                f"<div style='flex:1; background:#e9ecef; border-radius:4px; height:8px;'>"
                f"<div style='width:{ppct}%; background:#235036; height:100%; border-radius:4px;'></div>"
                f"</div>"
                f"<span style='font-size:0.75rem; color:#6c757d;'>{n_ann}/{n_tech}</span>"
                f"</div>", unsafe_allow_html=True,
            )

        # Combined technique distribution
        combined_by_tech = {}
        for a in combined_anns:
            t = a.get("technique", "unknown")
            combined_by_tech[t] = combined_by_tech.get(t, 0) + 1
        if combined_by_tech:
            st.markdown("**Combined techniques:**")
            for tech, cnt in sorted(combined_by_tech.items(), key=lambda x: x[1], reverse=True):
                disp = TECHNIQUE_DISPLAY_NAMES.get(tech, tech)
                st.caption(f"  {disp}: {cnt}")

    # Review all annotations
    st.markdown("---")
    annotations = ann_data.get("annotations", [])
    if annotations:
        with st.expander(f"Review All Annotations ({len(annotations)})", expanded=False):
            for i, ann in enumerate(annotations):
                tech_disp = TECHNIQUE_DISPLAY_NAMES.get(ann.get("technique", ""), ann.get("technique", ""))
                fc = ann.get("fighter_color", "?")
                fc_color = "#dc3545" if fc == "red" else "#0077B6" if fc == "blue" else "#6c757d"
                ts = ann.get("start_frame", 0)
                who = ann.get("annotated_by", "Unknown")

                ann_notes = ann.get("notes", "")
                notes_html = (f'<div style="font-size:0.75rem; color:#555; margin-top:2px; '
                              f'font-style:italic;">{ann_notes}</div>' if ann_notes else "")
                st.markdown(
                    f"<div style='background:#f8f9fa; border-radius:8px; padding:8px 12px; "
                    f"margin:4px 0; border-left:4px solid {fc_color};'>"
                    f"<strong style='color:{fc_color};'>{fc.upper()}</strong> "
                    f"<strong>{tech_disp}</strong> "
                    f"<span style='color:#6c757d; font-size:0.8rem;'>"
                    f"| {ann.get('target_zone', 'trunk')} | f{ts} | by {who}</span>"
                    f"{notes_html}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Edit button - jump back to this event
                if st.button(f"Edit", key=f"edit_ann_{i}"):
                    # Find matching event index
                    for ei, evt in enumerate(events):
                        if (evt.get("start_frame") == ann.get("start_frame") and
                                evt.get("end_frame") == ann.get("end_frame")):
                            st.session_state["event_idx"] = ei
                            st.session_state["page"] = "annotate"
                            st.rerun()

    # Download buttons
    st.markdown("---")
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            label="Download Annotations",
            data=json.dumps(ann_data, indent=2, ensure_ascii=False),
            file_name=f"{video_stem}_annotations.json",
            mime="application/json",
            use_container_width=True,
        )
    with dl2:
        matches_data = data_manager.load_matches()
        if matches_data:
            st.download_button(
                label="Download Match Groups",
                data=json.dumps(matches_data, indent=2, ensure_ascii=False),
                file_name="_matches.json",
                mime="application/json",
                use_container_width=True,
            )

    # Technique reference card
    with st.expander("Technique Reference (Coach Mehdi)"):
        for cat_name, cat_techs in TECHNIQUE_GROUPS.items():
            st.markdown(f"**{cat_name}**")
            for t in cat_techs:
                pts_info = ""
                if t in SPINNING_TECHNIQUES:
                    pts_info = " (4-5 pts, spinning)"
                elif t == "momtong_jireugi":
                    pts_info = " (1 pt)"
                elif t in ("block_defense", "neutral_stance"):
                    pts_info = " (0 pts)"
                else:
                    pts_info = " (2-3 pts)"
                st.markdown(f"- {TECHNIQUE_DISPLAY_NAMES.get(t, t)}{pts_info}")
            st.markdown("")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
page = st.session_state.get("page", "select")

if page == "select":
    page_select()
elif page == "annotate":
    page_annotate()
elif page == "progress":
    page_progress()
else:
    page_select()
