from typing import Optional, Union, Any, Dict
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.api.internal import TextWidget
from aiogram_dialog import DialogManager


class DynamicStyle(Style):
    def __init__(
            self,
            emoji_id: Optional[Union[str, TextWidget]] = None,
            style: Optional[Union[str, TextWidget]] = None,
            when: WhenCondition = None,
    ):
        super().__init__(when=when)
        self._emoji_id = emoji_id
        self._style = style

    async def render_emoji(
            self,
            data: Dict[str, Any],
            manager: DialogManager,
    ) -> Optional[str]:
        """Рендерит emoji_id — может быть строкой или виджетом"""
        if self._emoji_id is None:
            return None

        # Если это TextWidget — рендерим его
        if isinstance(self._emoji_id, TextWidget):
            return await self._emoji_id.render_text(data, manager)

        # Если это строка — возвращаем как есть
        return str(self._emoji_id)

    async def render_style(
            self,
            data: Dict[str, Any],
            manager: DialogManager,
    ) -> Optional[str]:
        """Рендерит style кнопки (цвет и т.д.)"""
        if self._style is None:
            return None

        if isinstance(self._style, TextWidget):
            return await self._style.render_text(data, manager)

        return str(self._style)