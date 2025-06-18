import React from "react";
import {withAPI} from "../../modules/api";
import {InputGroup} from "formik-blueprint";
import {MenuItem} from "@blueprintjs/core";
import {Suggest} from "@blueprintjs/select";
import "@blueprintjs/select/lib/css/blueprint-select.css";


const MIN_SEARCH_LENGTH = 3;


class DynamicSearch extends React.Component {
    state = {
        value: this.props.value,
        searchString: '',
        searchResults: null,
        suggestActiveItem: null,
    };

    constructor(props) {
        super(props);
        this.searchTimeout = null;
    }

    selectItem(item) {
        let change = {value: item.value};
        if (this.state.suggestActiveItem === null || this.state.suggestActiveItem.value !== item.value) {
            change.suggestActiveItem = item;
        }
        this.setState({...change});
        this.props.onChange(item ? item.value : null);
        return false;
    }

    renderItem(item, itemProps) {
        return <MenuItem key={item.value} text={item.label} active={itemProps.modifiers.active}
                         onClick={itemProps.handleClick}
        />
    };

    renderSingleSelect() {
        return (
            <div>
                <Suggest onQueryChange={query => {
                    this.handleQueryChange(query);
                }}
                         items={this.state.searchResults || []}
                         itemRenderer={((item, itemProps) => this.renderItem(item, itemProps))}
                         activeItem={this.state.suggestActiveItem}
                         inputValueRenderer={item => item.label}
                         onActiveItemChange={activeItem => {
                             if (activeItem !== this.state.suggestActiveItem && (activeItem === null || this.state.suggestActiveItem === null || activeItem.value !== this.state.suggestActiveItem.value)) {
                                 this.setState({suggestActiveItem: activeItem});
                             }
                         }}
                         onItemSelect={item => this.selectItem(item)}
                         inputProps={{
                             onKeyPress: e => {
                                 if (e.key === 'Enter') {
                                     e.preventDefault()
                                 }
                             },
                             placeholder: "Szukaj...",
                             ...this.props.inputProps,
                         }}
                         popoverProps={{minimal: true, fill: true}}
                         noResults={<MenuItem disabled={true}
                                              text={this.state.searchString.length >= MIN_SEARCH_LENGTH ?
                                                  "Nic nie znaleziono" : "Wprowadź co najmniej " + MIN_SEARCH_LENGTH + " znaki"}
                         />}
                />
            </div>
        );
    }

    renderMultiSelect() {
        return (
            <div>
                <span>dynamic search multi</span>
                <InputGroup onChange={(e) => this.handleChange(e)}
                            value={this.state.value || ''}/>
                <span>{JSON.stringify(this.state.widgetData)}</span>
            </div>
        );
    }

    render() {
        if (this.props.definition.multiselect) {
            return this.renderMultiSelect();
        } else {
            return this.renderSingleSelect();
        }
    }


    handleQueryChange(val) {
        this.setState({searchString: val});
        clearTimeout(this.searchTimeout);
        this.searchTimeout = null;

        val = val.trim();
        if (val.length >= MIN_SEARCH_LENGTH) {
            this.searchTimeout = setTimeout(() => {
                this.props.onWidgetDataNeed(val).then(resp => {
                    this.setState({searchResults: resp, suggestActiveItem: null});
                }, reason => {
                    console.log('DynamicSearch data error', reason);
                })
            }, 300);
        } else {
            this.setState({searchResults: null, suggestActiveItem: null});
        }
    }

}

export default withAPI(DynamicSearch);