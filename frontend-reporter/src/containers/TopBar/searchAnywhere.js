import React from 'react';
import SearchBox from "../../components/searchBox";
import {withAPI} from "../../modules/api";
import {Button} from "@blueprintjs/core";
import {Omnibar} from "@blueprintjs/select";


class SearchAnywhere extends React.Component {

    state = {
        searchBoxOpen: false,
        searchResults: [],

    };

    doSearch(query) {
        let query_l = query.toLowerCase();

        if (query_l.length === 0) {
            return;
        }
        if (query_l.length < 3) {
            return;
        }

        if(query.length > 3) {
            this.setState({'searchResults': [
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
        // let api = this.props.getREST();
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

    renderSearchResult(res) {
        return (
            <div>bla</div>
        )
    }

    selectSearchResult(res) {
        console.log('select', res)
    }

    render() {
        return (<div id="searchBoxContainer">
            <Button text="Szukaj..." icon="search" onClick={() => this.setState({searchBoxOpen: true})} minimal={true} />
            <Omnibar isOpen={this.state.searchBoxOpen} items={this.state.searchResults}
                     itemRenderer={item => this.renderSearchResult(item)} onItemSelect={item => this.selectSearchResult(item)}
                     onQueryChange={ (query, event) => this.doSearch(query) }
                     inputProps={{placeholder: 'Szukaj...'}} />
        </div>);

    }

    XXXrender() {
        return (
            <div id="searchBoxContainer">
                <SearchBox placeholder="Szukaj... [ctrl+/]" placeholderFocus="Szukaj..."
                           onSearch={(query, callback) => this.doSearch(query, callback)}
                           input
                           hotkey="ctrl+/" minLength="0" />
            </div>
        )
    }
}

export default withAPI(SearchAnywhere);
