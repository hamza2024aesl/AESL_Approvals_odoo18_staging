/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
const { DateTime } = luxon;

publicWidget.registry.AttendanceExpandButton = publicWidget.Widget.extend({
    selector: '.attendance-expand-btn',
    events: {
        'click': '_onExpandAttendanceGroupClick',
    },

    _onExpandAttendanceGroupClick(ev) {
        ev.preventDefault();

        const $btn = $(ev.currentTarget);
        const groupId = $btn.data('group-id');
        const $icon = $btn.find('.attendance-expand-icon');

        $(`.attendance-group-row[data-group-id="${groupId}"]`).toggle();
        $icon.toggleClass('fa-plus fa-minus');
    },
});

publicWidget.registry.CheckInOut = publicWidget.Widget.extend({
    selector: '#check_inout_portal',
    events: {
        click: '_onClick',
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
        this.dialog = this.bindService("dialog");
        this.http = this.bindService("http");
        this.employee = false;
        this.state = {
            checkedIn: false,
            isDisplayed: false,
        };
        this.date_formatter = function(value) {
            const hours = Math.floor(value);
            const minutes = Math.round((value - hours) * 60);
            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
        };
        this.searchReadEmployee();
    },

    async searchReadEmployee() {
        const result = await rpc("/my/attendance/attendance_user_data"); // Use rpc directly
        this.employee = result;
        if (this.employee.id) {
            this.hoursToday = this.date_formatter(
                this.employee.hours_today
            );
            this.hoursPreviouslyToday = this.date_formatter(
                this.employee.hours_previously_today
            );
            this.lastAttendanceWorkedHours = this.date_formatter(
                this.employee.last_attendance_worked_hours
            );
            this.lastCheckIn = deserializeDateTime(this.employee.last_check_in)
                               .toLocaleString(DateTime.TIME_SIMPLE);
            this.state.checkedIn = this.employee.attendance_state === "checked_in";
            this.isFirstAttendance = this.employee.hours_previously_today === 0;
            this.state.isDisplayed = this.employee.display_systray;
            const EmployeeName = this.employee.employee_name;
            $('#name_id').val(EmployeeName);
        }
    },

    async _onClick(e) {
        e.preventDefault();
        const loadingScreen = document.getElementById('loading-screen');
        showLoadingScreen();

        navigator.geolocation.getCurrentPosition(
            async ({coords: {latitude, longitude}}) => {
                await rpc("/my/attendance/systray_check_in_out", {
                    latitude,
                    longitude
                });
                await this.searchReadEmployee();
                hideLoadingScreen();
                window.location.reload();
            },
            async err => {
                hideLoadingScreen();
                alert("Location permission was denied. Please enable location access to mark your attendance.");
            }
        );

        function showLoadingScreen() {
            loadingScreen.classList.remove('hidden');
        }

        function hideLoadingScreen() {
            loadingScreen.classList.add('hidden');
        }
    },
});

publicWidget.registry.AttendanceGroupBy = publicWidget.Widget.extend({
    selector: '.attendance-groupby-container',

    start() {
        const checkboxes = document.querySelectorAll('.group-by-checkbox-attendances');
        const subordinateSwitch = document.getElementById('attendance-sub-ordinates');
        const currentParams = new URLSearchParams(window.location.search);

        checkboxes.forEach(checkbox => {
            if (currentParams.get('group_by') === checkbox.value) {
                checkbox.checked = true;
            }

            checkbox.addEventListener('change', function () {
                const updatedParams = new URLSearchParams(window.location.search);

                if (this.checked) {
                    checkboxes.forEach(cb => {
                        if (cb !== this) cb.checked = false;
                    });
                    updatedParams.set('group_by', this.value);
                } else {
                    updatedParams.delete('group_by');
                }

                window.location.href = `${window.location.pathname}?${updatedParams.toString()}`;
            });
        });

        if (subordinateSwitch) {
            subordinateSwitch.checked = currentParams.get('subordinate') === '1';

            subordinateSwitch.addEventListener('change', function () {
                const updatedParams = new URLSearchParams(window.location.search);

                if (this.checked) {
                    updatedParams.set('subordinate', '1');
                } else {
                    updatedParams.delete('subordinate');
                }

                window.location.href = `${window.location.pathname}?${updatedParams.toString()}`;
            });
        }
        return this._super(...arguments);
    },
});