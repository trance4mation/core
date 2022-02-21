"""The Backup integration."""
from homeassistant.components.hassio import is_hassio
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, LOGGER
from .http import async_register_http_views
from .manager import BackupManager
from .websocket import async_register_websocket_handlers


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Backup integration."""
    if is_hassio(hass):
        LOGGER.warning(
            "The backup integration is not supported on this installation method, "
            "please remove it from your configuration"
        )
        return False

    hass.data[DOMAIN] = BackupManager(hass)

    async_register_websocket_handlers(hass)
    async_register_http_views(hass)

    return True