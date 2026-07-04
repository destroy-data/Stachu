/*
 * SPDX-FileCopyrightText: 2026 M5Stack Technology CO LTD
 *
 * SPDX-License-Identifier: MIT
 */
#include "hal.h"
#include "utils/bleprph/bleprph.h"
#include "utils/secret_logic/secret_logic.h"
#include <ArduinoJson.hpp>
#include <mooncake_log.h>
#include <mooncake.h>
#include <settings.h>
#include <esp_mac.h>

static const std::string_view _tag = "HAL-BLE";

static int _handle_ble_motion_write(const char* json_data, uint16_t len, uint16_t conn_handle)
{
    // mclog::tagInfo(_tag, "on motion:\n{}", json_data);
    GetHAL().onBleMotionData.emit(json_data);
    return 0;
}

static int _handle_ble_avatar_write(const char* json_data, uint16_t len, uint16_t conn_handle)
{
    // mclog::tagInfo(_tag, "on avatar:\n{}", json_data);
    GetHAL().onBleAvatarData.emit(json_data);
    return 0;
}

static int _handle_ble_rgb_write(const char* json_data, uint16_t len, uint16_t conn_handle)
{
    // mclog::tagInfo(_tag, "on rgb:\n{}", json_data);
    GetHAL().onBleRgbData.emit(json_data);
    return 0;
}

static uint8_t _handle_ble_battery_read(void)
{
    mclog::tagInfo(_tag, "on bat read");
    return 96;
}

void Hal::ble_init(bool useAltUuid)
{
    mclog::tagInfo(_tag, "init");

    static stackchan_ble_callbacks_t ble_callbacks = {
        .motion_cb       = _handle_ble_motion_write,
        .avatar_cb       = _handle_ble_avatar_write,
        .config_cb       = nullptr,
        .rgb_cb          = _handle_ble_rgb_write,
        .battery_read_cb = _handle_ble_battery_read,
    };
    stackchan_ble_register_callbacks(&ble_callbacks);

    ble_prph_init(useAltUuid);

    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_EFUSE_FACTORY);
    mclog::tagInfo(_tag, "init done, factory mac: {:02x}:{:02x}:{:02x}:{:02x}:{:02x}:{:02x}", mac[0], mac[1], mac[2],
                   mac[3], mac[4], mac[5]);
}

void Hal::startBleServer()
{
    mclog::tagInfo(_tag, "start ble server");
    ble_init(false);
}

bool Hal::isBleConnected()
{
    return stackchan_ble_is_connected();
}

bool Hal::isConfigured()
{
    Settings settings("config", false);
    return settings.GetBool("is_configured", false);
}

void Hal::setConfigured()
{
    Settings settings("config", true);
    settings.SetBool("is_configured", true);
}
