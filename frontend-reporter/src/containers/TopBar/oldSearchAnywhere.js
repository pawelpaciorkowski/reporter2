import React from 'react';
import {NavLink} from "react-router-dom";
import SearchBox from "../../components/searchBox";
import {withAPI} from "../../modules/api";


class SearchAnywhere extends React.Component {

    doSearch(query, callback) {
        let query_l = query.toLowerCase();

        if (query_l.length === 0) {
            callback({
                'status': 'info',
                'msg': 'Wprowadź co najmniej 3 znaki. Wyszukuj [litera][spacja][szukany tekst] dla liter:\n - l - laboratoria\n - k - klienci\n - z - złączki\n - c - szukaj tekstu w komentarzach\nDomyślne wyszukiwanie po laboratoriach, złączkach i klientach podłączonych pod złączki.'
            });
            return;
        }
        if (query_l.length < 3) {
            callback({
                'status': 'info',
                'msg': 'Wprowadź co najmniej 3 znaki.'
            });
            return;
        }

        let api = this.props.getREST();
        if(query.length > 3) {
            callback({'results': [
                    {title: 'Test', helper: 'Test 2', url: 'test'},
                    {title: 'Test', helper: 'Test 2', url: 'test'},
                    {title: 'Test', helper: 'Test 2', url: 'test'},
                    {title: 'Test', helper: 'Test 2', url: 'test'},
                    {title: 'Test', helper: 'Test 2', url: 'test'},
                    {title: 'Test', helper: 'Test 2', url: 'test'},
                    {title: 'Test', helper: 'Test 2', url: 'test'},
                    {title: 'Test', helper: 'Test 2', url: 'test'},
                    {title: 'Test', helper: 'Test 2', url: 'test'},
                ]});
        }
        // api.get('szukaj/?q=' + encodeURIComponent(query)).then((resp) => {
        //     let res = [];
        //     for(let resp_row of resp) {
        //         let row = null;
        //         if(resp_row['typ'] === 'lab') {
        //             row = {
        //                 title: resp_row['symbol'] + ' - ' + resp_row['nazwa'],
        //                 helper: 'laboratorium',
        //                 url: '/laby/' + resp_row['symbol'],
        //             };
        //         }
        //         if(resp_row['typ'] === 'klient') {
        //             row = {
        //                 title: resp_row['nazwa'],
        //                 helper: 'klient',
        //                 url: '/klienci/' + resp_row['id'],
        //             };
        //             if(resp_row['zlaczki'] > 0) {
        //                 row['title'] += ' (' + resp_row['zlaczki'] + ' zlaczek)';
        //             }
        //         }
        //         if(resp_row['typ'] === 'zlaczka') {
        //             row = {
        //                 title: resp_row['nazwa'],
        //                 helper: 'zlaczka',
        //                 url: '/laby/' + resp_row['lab'] + '/z/' + resp_row['nazwa'],
        //             };
        //             if(resp_row['zlaczki'] > 0) {
        //                 row['title'] += ' (' + resp_row['zlaczki'] + ' zlaczek)';
        //             }
        //         }
        //         if(row !== null) {
        //             res.push(row);
        //         }
        //     }
        //     if(res.length > 0) {
        //         callback({'results': res});
        //     } else {
        //         callback({'status': 'warning', 'msg': 'Nic nie znaleziono.'});
        //     }
        // });
    }

    render() {
        return (
            <div id="searchBoxContainer">
                <SearchBox placeholder="Szukaj... [ctrl+/]" placeholderFocus="Szukaj..."
                           onSearch={(query, callback) => this.doSearch(query, callback)}
                           hotkey="ctrl+/" minLength="0" />
            </div>
        )
    }
}

export default withAPI(SearchAnywhere);
