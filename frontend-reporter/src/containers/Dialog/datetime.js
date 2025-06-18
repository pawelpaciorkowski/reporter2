import React from "react";
import {DateInput} from "@blueprintjs/datetime";

const MONTHS = [
    'styczeń', 'luty', 'marzec',
    'kwiecień', 'maj', 'czerwiec',
    'lipiec', 'sierpień', 'wrzesień',
    'październik', 'listopad', 'grudzień'
];
const WEEKDAYS_LONG = [
    'niedziela', 'poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota'
];
const WEEKDAYS_SHORT = ['nd', 'pn', 'wt', 'śr', 'cz', 'pt', 'sb'];

// TODO: obsługa wyboru godziny

class DateTime extends React.Component {
    onChange(date, changed) {
        if (changed) {
            this.props.onChange(this.formatDate(date));
        }
    }

    parseDate(str) {
        if(str === null || str === '') {
            return null;
        }
        let trimmedStr = str.trim().toUpperCase();
        // T - teraz
        if (trimmedStr === 'T') {
            return new Date();
        }
        // +2D, 3D, -7D - dodawanie i odejmowanie dni od bieżącej daty
        if (trimmedStr[trimmedStr.length - 1] === 'D') {
            trimmedStr = trimmedStr.replace('+', '');
            let dir = 1;
            let days = 0;
            if (trimmedStr[0] === '-') {
                dir = -1;
                days = parseInt(trimmedStr.substr(1, trimmedStr.length - 2));
            } else {
                days = parseInt(trimmedStr.substr(0, trimmedStr.length - 1));
            }
            let date = new Date();
            date.setDate(date.getDate() + dir * days);
            return date;
        }
        // PM, KM, PZM, KZM - początek/koniec [zeszłego] miesiąca
        if (['PM', 'KM', 'PZM', 'KZM'].indexOf(trimmedStr) !== -1) {
            let date = new Date();
            if (trimmedStr.indexOf('Z') !== -1) {
                date.setMonth(date.getMonth() - 1);
            }
            if (trimmedStr[0] === 'P') {
                date.setDate(1);
            } else if (trimmedStr[0] === 'K') {
                date.setMonth(date.getMonth() + 1);
                date.setDate(0);
            }
            return date;
        }
        return new Date(str);
    }

    formatDate(date) {
        if(date === null) {
            return null;
        }
        var month = '' + (date.getMonth() + 1),
            day = '' + date.getDate(),
            year = date.getFullYear();
        if (month.length < 2)
            month = '0' + month;
        if (day.length < 2)
            day = '0' + day;
        return [year, month, day].join('-');
    }

    render() {
        return <DateInput {...this.props.basicAttrs} onChange={(date, changed) => this.onChange(date, changed)}
                          value={this.parseDate(this.props.value || null)}
                          formatDate={date => this.formatDate(date)}
                          parseDate={str => this.parseDate(str)}
                          canClearSelection={this.props.canClearSelection}
                          placeholder={'RRRR-MM-DD'}
                          dayPickerProps={{
                              months: MONTHS,
                              weekdaysLong: WEEKDAYS_LONG,
                              weekdaysShort: WEEKDAYS_SHORT,
                              firstDayOfWeek: 1,
                              locale: 'pl',
                              fixedWeeks: true,

                          }}
                          shortcuts={false}
                          minDate={new Date(1900, 1, 1)}
                          maxDate={new Date(2100, 12, 31)}


        />;
    }


}

export default DateTime;
export {MONTHS, WEEKDAYS_LONG, WEEKDAYS_SHORT}