import React from "react";
import './searchBox.css';
import {withKeyCtrl} from "../modules/keyCtrl";
import {withRouter} from "react-router-dom";


class SearchBox extends React.Component {
    state = {
        isFocused: false,
        inputValue: '',
        showPopup: false,
        searchResults: null,
        selectedResult: null,
        infoBox: null,
    };

    constructor(props) {
        super(props);
        this.input = React.createRef();
        this.keyCallbacks = {};
        this.keyTimeout = null;
    }

    subscribeKey(key, callback) {
        this.keyCallbacks[key] = callback;
        this.props.keyCtrlSubscribe(key, callback);
    }

    unsubscribeKey(key) {
        if (this.keyCallbacks[key]) {
            this.props.keyCtrlUnsubscribe(key);
            this.keyCallbacks[key] = undefined;
        }
    }

    unsubscribeAllKeys() {
        for (let key of Object.keys(this.keyCallbacks)) {
            this.unsubscribeKey(key);
        }
    }

    abort() {
        this.input.current.blur();
    }

    inputFocus(e) {
        this.setState({
            isFocused: true,
        });
        this.subscribeKey('esc', () => this.abort());
        this.subscribeKey('up', () => this.moveCursor(-1));
        this.subscribeKey('down', () => this.moveCursor(1));
        this.subscribeKey('enter', () => this.selectCurrentResult());
        if (this.validateInputValue()) {
            this.props.onSearch(this.getValueForSearch(), (resp) => {
                this.processSearchResponse(resp);
            })
        }
    }

    inputBlur(e) {
        setTimeout(() => {
            this.setState({
                isFocused: false,
                inputValue: '',
                showPopup: false,
            });
            this.unsubscribeKey('esc');
            this.unsubscribeKey('up');
            this.unsubscribeKey('down');
            this.unsubscribeKey('enter');
        }, 10);
    }

    inputChange(e) {
        let val = e.target.value;
        this.setState({
            inputValue: val,
        });
        if (this.keyTimeout !== null) {
            clearTimeout(this.keyTimeout);
        }
        // TODO: być może tu czyścić istniejące wyniki wyszukiwania
        if (!this.validateInputValue()) {
            return;
        }
        this.keyTimeout = setTimeout(() => {
            if (this.state.inputValue === val) {
                this.props.onSearch(this.getValueForSearch(), (resp) => {
                    if (this.state.inputValue === val) {
                        this.processSearchResponse(resp);
                    }
                });
            }
        }, 300);
    }

    doSearch(val) {
        this.props.onSearch(val, (resp) => {
            this.processSearchResponse(resp);
        });
    }

    getValueForSearch() {
        return this.state.inputValue.trim();
    }

    validateInputValue() {
        let res = true;
        if (this.props.minLength !== undefined) {
            let minLength = parseInt(this.props.minLength);
            if (this.getValueForSearch().length < minLength) {
                res = false;
            }
        }
        return res;
    }

    processSearchResponse(resp) {
        let showPopup = false;
        let searchResults = null;
        let selectedResult = null;
        let prefixes = null;
        let infoBox = null;
        if (resp.hasOwnProperty('prefixes') && resp['prefixes'] !== null) {
            prefixes = (<div>{resp['prefixes'].map(pref => {
                return <span className="prefix" onMouseDown={e => {
                    let val = pref[0] + ' ';
                    this.setState({
                        inputValue: val,
                        isFocused: true,
                        showPopup: true,
                    });
                    this.doSearch(val);
                    e.preventDefault();
                    return false;
                }}>
                    <span className="prefixShortcut">{pref[0]}</span>
                    <span className="prefixName">{pref[1]}</span>
                </span>
            })}</div>)
        }
        if (resp.hasOwnProperty('msg')) {
            showPopup = true;
            let infoBoxClasses = "searchBoxInfobox";
            if (resp.hasOwnProperty('status')) {
                infoBoxClasses += " searchBoxInfobox_" + resp['status'];
            }
            infoBox = <div className={infoBoxClasses}>{resp['msg']}{prefixes}</div>;
        }
        if (resp.hasOwnProperty('results')) {
            showPopup = true;
            searchResults = resp['results'];
            selectedResult = -1;
        }
        this.setState({showPopup, searchResults, selectedResult, infoBox});
    }

    setActiveResultRow(row_no) {
        this.setState({selectedResult: row_no});
    }

    selectResultRow(row_no) {
        this.props.onBeacon({
            query: this.state.inputValue,
            result: this.state.searchResults[row_no],
            result_idx: row_no,
        })
        this.props.history.push(this.state.searchResults[row_no]['url']);
    }

    moveCursor(step) {
        let selectedResult = this.state.selectedResult;
        if (selectedResult === null || this.state.searchResults === null || this.state.searchResults.length === 0) {
            return;
        }
        selectedResult = (selectedResult + step) % this.state.searchResults.length;
        if(selectedResult < 0) {
            selectedResult = -1;
        }
        this.setState({selectedResult});
    }

    selectCurrentResult() {
        let selectedResult = this.state.selectedResult;
        if (selectedResult === null || selectedResult === undefined || this.state.searchResults === null || this.state.searchResults.length === 0) {
            return;
        }
        if (this.state.searchResults[selectedResult] === undefined) {
            return;
        }
        let url = this.state.searchResults[selectedResult]['url'];
        this.props.onBeacon({
            query: this.state.inputValue,
            result: this.state.searchResults[selectedResult],
            result_idx: selectedResult,
        })
        this.props.history.push(url);
        this.abort();
    }

    componentDidMount() {
        if (this.props.hotkey) {
            this.subscribeKey(this.props.hotkey, () => {
                if (this.state.isFocused) {
                    this.abort();
                } else {
                    this.input.current.focus();
                }
            });
        }
    }

    componentWillUnmount() {
        this.unsubscribeAllKeys();
    }

    render() {
        let containerClasses = "searchBoxBundle";
        if (this.state.isFocused) {
            containerClasses += " searchBoxBundleFocused";
        }
        if (this.state.showPopup) {
            containerClasses += " searchBoxBundleShowPopup";
        }
        return (
            <div className={containerClasses}>
                <input type="text" className="searchBoxInput bp3-input" value={this.state.inputValue} ref={this.input}
                       placeholder={(this.state.isFocused && this.props.placeholderFocus !== undefined) ?
                           this.props.placeholderFocus : this.props.placeholder}
                       onFocus={(e) => this.inputFocus(e)}
                       onBlur={(e) => {
                           setTimeout(() => {
                               this.inputBlur(e);
                           }, 50);
                       }}
                       onChange={(e) => this.inputChange(e)}
                />
                {this.state.showPopup ? (
                    <div className="searchBoxPopup">
                        {this.state.searchResults ?
                            <div className="searchBoxResults">
                                {this.state.searchResults.map((result, idx) => {
                                    let classes = "searchBoxResult";
                                    if (idx === this.state.selectedResult) {
                                        classes += " searchBoxResultActive";
                                    }
                                    return (
                                        <div className={classes} key={idx}
                                             onMouseMove={(e) => {
                                                 if (this.state.selectedResult !== idx) {
                                                     this.setActiveResultRow(idx)
                                                 }
                                             }} onMouseDown={(e) => this.selectResultRow(idx)}
                                        >
                                            <div className="searchBoxResultTitle">{result['title']}</div>
                                            {result['helper'] ?
                                                <div className="searchBoxResultHelper">{result['helper']}</div> : null}
                                            <div className="searchBoxResultClear"></div>
                                        </div>
                                    );
                                })}
                            </div> : null
                        }
                        {this.state.infoBox}
                    </div>
                ) : null}
            </div>
        );
    }
}


export default withRouter(withKeyCtrl(SearchBox));
