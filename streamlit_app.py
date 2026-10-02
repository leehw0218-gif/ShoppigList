"""쇼핑리스트 - Streamlit 버전 (prd.md 기준, 웹 버전 app.js를 옮김)

실행: streamlit run streamlit_app.py
데이터는 localStorage 대신 같은 폴더의 shopping_list.json에 저장한다.
"""

import html
import json
import math
import random
import string
import time
from pathlib import Path

import streamlit as st

DATA_FILE = Path(__file__).with_name("shopping_list.json")
MAX_NAME_LENGTH = 50
MIN_QUANTITY = 1
MAX_QUANTITY = 99


# ---------- 데이터 정규화 ----------


def normalize_name(name) -> str:
    """trim 후 최대 길이로 자름. 빈 값이면 '' 반환"""
    return str(name or "").strip()[:MAX_NAME_LENGTH]


def normalize_quantity(value, fallback: int = MIN_QUANTITY) -> int:
    """정수로 바꿔 1~99 범위로 맞춤. 숫자가 아니면 fallback 반환"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if not math.isfinite(number):
        return fallback
    return min(MAX_QUANTITY, max(MIN_QUANTITY, int(number)))


def generate_id() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{int(time.time() * 1000):x}{suffix}"


def is_valid_item(item) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("name"), str)
        and item["name"].strip() != ""
    )


# ---------- 저장 / 불러오기 ----------


def load_items() -> list[dict]:
    try:
        parsed = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # 파일 없음 / 읽기 불가 / 깨진 JSON → 빈 목록으로 시작
        return []
    if not isinstance(parsed, list):
        return []
    return [
        {
            "id": item["id"],
            "name": normalize_name(item["name"]),
            "quantity": normalize_quantity(item.get("quantity")),  # 수량 없는 기존 데이터는 1개
            "checked": bool(item.get("checked")),
            "createdAt": item.get("createdAt") or int(time.time() * 1000),
        }
        for item in parsed
        if is_valid_item(item)
    ]


def save_items() -> None:
    try:
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(st.session_state.shopping_items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(DATA_FILE)
    except OSError:
        # 저장 불가 환경에서도 앱은 세션 상태로 계속 동작
        pass


def find_item(item_id: str) -> dict | None:
    return next((it for it in st.session_state.shopping_items if it["id"] == item_id), None)


# ---------- 기능 (F-1 ~ F-4) ----------


def add_item() -> None:
    """F-1 아이템 추가 (추가 폼 제출 콜백)"""
    name = normalize_name(st.session_state.new_name)
    if not name:
        return
    st.session_state.shopping_items.append(
        {
            "id": generate_id(),
            "name": name,
            "quantity": normalize_quantity(st.session_state.new_quantity),
            "checked": False,
            "createdAt": int(time.time() * 1000),
        }
    )
    save_items()


def start_editing(item_id: str) -> None:
    # 다른 아이템 편집 중이었다면 그 편집은 취소됨
    item = find_item(item_id)
    if not item:
        return
    st.session_state.editing_id = item_id
    st.session_state[f"edit_name_{item_id}"] = item["name"]
    st.session_state[f"edit_qty_{item_id}"] = item["quantity"]


def cancel_editing() -> None:
    st.session_state.editing_id = None


def update_item(item_id: str) -> None:
    """F-2 이름·수량 수정. 빈 값이면 각각 원래 값 유지"""
    item = find_item(item_id)
    if item:
        item["name"] = normalize_name(st.session_state[f"edit_name_{item_id}"]) or item["name"]
        item["quantity"] = normalize_quantity(
            st.session_state[f"edit_qty_{item_id}"], item["quantity"]
        )
        save_items()
    st.session_state.editing_id = None


def toggle_item(item_id: str) -> None:
    """F-4 체크 토글"""
    item = find_item(item_id)
    if not item:
        return
    item["checked"] = st.session_state[f"check_{item_id}"]
    save_items()


@st.dialog("아이템 삭제")
def confirm_delete(item_id: str) -> None:
    """F-3 삭제 전 확인"""
    item = find_item(item_id)
    if not item:
        st.rerun()
    st.write(f"\"{item['name']}\"을(를) 삭제할까요?")
    col_ok, col_cancel = st.columns(2)
    if col_ok.button("삭제", type="primary", use_container_width=True):
        st.session_state.shopping_items = [it for it in st.session_state.shopping_items if it["id"] != item_id]
        if st.session_state.editing_id == item_id:
            st.session_state.editing_id = None
        save_items()
        st.rerun()
    if col_cancel.button("취소", use_container_width=True):
        st.rerun()


# ---------- 화면 ----------

ITEM_STYLE = """
<style>
.sl-row { display: flex; align-items: center; gap: 8px; min-height: 40px; }
.sl-name { flex: 1 1 auto; min-width: 0; overflow-wrap: anywhere; word-break: keep-all; }
.sl-name.checked { text-decoration: line-through; text-decoration-thickness: 2px; opacity: 0.65; }
.sl-qty {
  flex: 0 0 auto; padding: 1px 8px; border-radius: 999px;
  border: 1px solid rgba(128, 128, 128, 0.35); font-size: 0.85rem; font-weight: 600;
  white-space: nowrap; font-variant-numeric: tabular-nums;
}
</style>
"""


def render_item_label(item: dict) -> None:
    # 사용자 입력은 html.escape로 이스케이프 (XSS 방지)
    checked = " checked" if item["checked"] else ""
    st.html(
        f'{ITEM_STYLE}<div class="sl-row">'
        f'<span class="sl-name{checked}">{html.escape(item["name"])}</span>'
        f'<span class="sl-qty" aria-label="{item["quantity"]}개">× {item["quantity"]}</span>'
        f"</div>"
    )


def render_edit_row(item: dict) -> None:
    item_id = item["id"]
    with st.form(f"edit_form_{item_id}", border=False):
        col_name, col_qty = st.columns([4, 1.4], vertical_alignment="bottom")
        col_name.text_input(
            "이름 수정",
            key=f"edit_name_{item_id}",
            max_chars=MAX_NAME_LENGTH,
            label_visibility="collapsed",
        )
        col_qty.number_input(
            "수량 수정",
            key=f"edit_qty_{item_id}",
            min_value=MIN_QUANTITY,
            max_value=MAX_QUANTITY,
            step=1,
            label_visibility="collapsed",
        )
        col_save, col_cancel, _ = st.columns([1, 1, 3])
        # Enter 키는 첫 번째 제출 버튼(저장)으로 처리됨
        col_save.form_submit_button(
            "저장", type="primary", on_click=update_item, args=(item_id,), use_container_width=True
        )
        col_cancel.form_submit_button("취소", on_click=cancel_editing, use_container_width=True)


def render_item(item: dict) -> None:
    item_id = item["id"]
    editing = st.session_state.editing_id == item_id

    with st.container(border=True):
        col_check, col_body, col_edit, col_delete = st.columns(
            [0.5, 5, 1.1, 1.1], vertical_alignment="center", gap="small"
        )
        col_check.checkbox(
            f"{item['name']} {item['quantity']}개 구매 완료",
            value=item["checked"],
            key=f"check_{item_id}",
            on_change=toggle_item,
            args=(item_id,),
            label_visibility="collapsed",
        )
        if editing:
            with col_body:
                render_edit_row(item)
        else:
            with col_body:
                render_item_label(item)
            col_edit.button(
                "수정",
                key=f"edit_{item_id}",
                on_click=start_editing,
                args=(item_id,),
                use_container_width=True,
            )
            if col_delete.button("삭제", key=f"delete_{item_id}", use_container_width=True):
                confirm_delete(item_id)


def main() -> None:
    st.set_page_config(page_title="쇼핑리스트", page_icon="🛒", layout="centered")

    if "shopping_items" not in st.session_state:
        st.session_state.shopping_items = load_items()
        st.session_state.editing_id = None

    st.title("🛒 쇼핑리스트")

    # F-1 입력 폼 (Enter 또는 추가 버튼으로 제출)
    with st.form("add_form", clear_on_submit=True, border=True):
        col_name, col_qty, col_btn = st.columns([5, 1.5, 1.2], vertical_alignment="bottom")
        col_name.text_input(
            "살 물건",
            key="new_name",
            placeholder="살 물건을 입력하세요",
            max_chars=MAX_NAME_LENGTH,
            label_visibility="collapsed",
        )
        col_qty.number_input(
            "수량",
            key="new_quantity",
            min_value=MIN_QUANTITY,
            max_value=MAX_QUANTITY,
            value=MIN_QUANTITY,
            step=1,
            label_visibility="collapsed",
        )
        col_btn.form_submit_button(
            "추가", type="primary", on_click=add_item, use_container_width=True
        )

    items = st.session_state.shopping_items

    # F-5 상태 표시
    if not items:
        st.info("쇼핑리스트가 비어 있어요. 살 물건을 추가해 보세요!")
        return

    done = sum(1 for it in items if it["checked"])
    st.progress(done / len(items), text=f"{done} / {len(items)} 완료")

    for item in items:
        render_item(item)


main()
