"""Sensoren der PV Übersicht."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN
from .tracker import PVTracker

if TYPE_CHECKING:
    from . import PVConfigEntry

KWH_PER_DAY = "kWh/d"


@dataclass(frozen=True, kw_only=True)
class PVSensorDescription(SensorEntityDescription):
    value_fn: Callable[[PVTracker], StateType]
    attrs_fn: Callable[[PVTracker], dict[str, Any]] | None = None


def _energy(key: str, data_key: str, state_class: SensorStateClass | None, **kwargs: Any) -> PVSensorDescription:
    return PVSensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=state_class,
        suggested_display_precision=2,
        value_fn=lambda t: round(t.data[data_key], 4),
        **kwargs,
    )


def _average(key: str, days: int | None) -> PVSensorDescription:
    return PVSensorDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=KWH_PER_DAY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:chart-line",
        value_fn=lambda t: None if (v := t.average_daily(days)) is None else round(v, 3),
    )


SENSORS: tuple[PVSensorDescription, ...] = (
    _energy("total", "total_kwh", SensorStateClass.TOTAL_INCREASING, icon="mdi:solar-power-variant"),
    _energy("today", "day_kwh", SensorStateClass.TOTAL_INCREASING, icon="mdi:solar-power"),
    _energy(
        "yesterday",
        "yesterday_kwh",
        None,
        icon="mdi:calendar-arrow-left",
        attrs_fn=lambda t: {"history": t.recent_days(30)},
    ),
    _energy("week", "week_kwh", SensorStateClass.TOTAL_INCREASING, icon="mdi:calendar-week"),
    _energy(
        "month",
        "month_kwh",
        SensorStateClass.TOTAL_INCREASING,
        icon="mdi:calendar-month",
        attrs_fn=lambda t: {"months": dict(sorted(t.data["months"].items()))},
    ),
    _energy("last_month", "last_month_kwh", None, icon="mdi:calendar-arrow-left"),
    _energy("year", "year_kwh", SensorStateClass.TOTAL_INCREASING, icon="mdi:calendar"),
    PVSensorDescription(
        key="max_power_today",
        translation_key="max_power_today",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:flash-alert",
        value_fn=lambda t: round(t.data["day_max_w"], 1),
        attrs_fn=lambda t: {"time": t.data["day_max_time"]},
    ),
    PVSensorDescription(
        key="max_power_alltime",
        translation_key="max_power_alltime",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        icon="mdi:trophy",
        value_fn=lambda t: round(t.data["alltime_max_w"], 1),
        attrs_fn=lambda t: {"time": t.data["alltime_max_time"]},
    ),
    PVSensorDescription(
        key="avg_power_today",
        translation_key="avg_power_today",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        icon="mdi:approximately-equal",
        value_fn=lambda t: round(t.average_power_today(), 1),
    ),
    PVSensorDescription(
        key="production_time_today",
        translation_key="production_time_today",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:timer-sun",
        value_fn=lambda t: round(t.data["day_active_s"] / 3600, 3),
    ),
    _average("avg_daily_7", 7),
    _average("avg_daily_30", 30),
    _average("avg_daily_365", 365),
    _average("avg_daily_total", None),
    PVSensorDescription(
        key="best_day",
        translation_key="best_day",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        icon="mdi:medal",
        value_fn=lambda t: round(t.best_day()[0], 3),
        attrs_fn=lambda t: {"date": t.best_day()[1]},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PVConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    tracker = entry.runtime_data
    async_add_entities(PVOverviewSensor(tracker, entry, desc) for desc in SENSORS)


class PVOverviewSensor(SensorEntity):
    """Ein Statistikwert der PV-Anlage."""

    entity_description: PVSensorDescription
    _attr_has_entity_name = True
    _attr_should_poll = False
    # Verlaufslisten nicht bei jeder Änderung in die Datenbank schreiben
    _unrecorded_attributes = frozenset({"history", "months"})

    def __init__(self, tracker: PVTracker, entry: PVConfigEntry, description: PVSensorDescription) -> None:
        self.entity_description = description
        self._tracker = tracker
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="PV Übersicht",
            model=tracker.source_entity,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self._tracker.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self._tracker)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self._tracker)
