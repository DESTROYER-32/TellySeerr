from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def create_media_pagination_markup(
    query: str,
    current_index: int,
    total_results: int,
    media_type: str,
    tmdb_id: int,
    is_requested: bool = False,
) -> InlineKeyboardMarkup:
    buttons = []

    # Only show navigation buttons if there's more than one result
    if total_results > 1:
        nav_row = []
        if current_index > 0:
            nav_row.append(
                InlineKeyboardButton(
                    text="⬅️ Previous",
                    callback_data=f"media_nav:prev:{current_index}:{query}",
                )
            )
        else:
            nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        if current_index < total_results - 1:
            nav_row.append(
                InlineKeyboardButton(
                    text="Next ➡️",
                    callback_data=f"media_nav:next:{current_index}:{query}",
                )
            )
        else:
            nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
        buttons.append(nav_row)

    if is_requested:
        buttons.append(
            [InlineKeyboardButton(text="✅ Requested", callback_data="noop")]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton(
                    text="Request", callback_data=f"media_req:{media_type}:{tmdb_id}"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_requests_pagination_markup(
    user_id: int, current_index: int, total_results: int
) -> InlineKeyboardMarkup:
    buttons = []
    nav_row = []

    if current_index > 0:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"req_nav:prev:{current_index}:{user_id}",
            )
        )
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

    if current_index < total_results - 1:
        nav_row.append(
            InlineKeyboardButton(
                text="Next ➡️", callback_data=f"req_nav:next:{current_index}:{user_id}"
            )
        )
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

    buttons.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)
