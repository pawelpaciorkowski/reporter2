import React from "react";
import {withAPI} from "../../modules/api";
import {HTMLSelect, Switch, Spinner} from "@blueprintjs/core";
class DynamicSelect extends React.Component {
    state = {
        widgetData: null,
    };

    componentDidMount() {
        const field_id = this.props.id;
        const default_data = this.props.defaultData;
        if (this.hasDefaultValue())(
            this.setState({widgetData: default_data[field_id]})
        )
        this.reloadIfNeeded();
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        if (this.props.value === 'Brak roli') {
        }
        this.reloadIfNeeded()
    }

    reloadIfNeeded() {

        if (this.state.widgetData === null && !this.hasDefaultValue()) {
            this.props.onWidgetDataNeed().then(resp => {
                this.setState({widgetData: resp});
                if ((this.props.value === null || this.props.value === undefined)
                    && !this.props.definition.multiselect) {
                    if (resp !== null && resp.length > 0) {
                        this.props.onValueChange(resp[0].value);
                    }
                }
            });
        }
    }

    hasDefaultValue() {
        const field_id = this.props.id;
        const default_data = this.props.defaultData;

        if(default_data === undefined) {
            return false;
        }

        return default_data[field_id] !== undefined;
    }

    renderMultiSelect() {
        let switch_id =  this.props.id+'_select_all';
        let selectRef = React.createRef();
        let changeSelechAll = (e) => {
            let checked = e.target.checked;
            for (var cld of selectRef.current.children) {
                cld.selected = checked;
            }
            selectRef.current.dispatchEvent(new Event('change', { bubbles: true }));
        };

        // const isAllInDefaultData = () => {
        //     if (Array.isArray(this.props.defaultData) && (this.props.defaultData.includes('*'))) {
        //     return true
        //     }
        //     return false
        // }

        // const hasDefaultVal = () => {
        //     if (this.props.defaultData) {
        //         return true
        //     }
        //     return false
        // }


        let defaultDataAsArray = () => {
            // Nie działa z * 
            if (this.props.defaultData && this.props.defaultData[0]) {
                if (this.props.defaultData[0] === '*') {
                    return this.state.widgetData.map(o => o.value)
                }
                const resp = this.props.defaultData[0].split(' ');
                return resp
            }

        }

        let collectSelected = () => {

            let selected = [];
            for(var cld of selectRef.current.children) {
                if(cld.selected) {
                    selected.push(cld.value);
                }
            }
            this.props.onValueChange(selected.join(' '));
        };

        // const defaultSelectAll = () => {
        //     if (!hasDefaultVal()) {
        //         return false;
        //     }
        //     return isAllInDefaultData()
        // }

        return (<div>
            <select style={{width: '90%'}} multiple={true} size={8} ref={selectRef}
                    onChange={() => collectSelected()}
                title="Kliknij przytrzymując CTRL lub SHIFT aby zaznaczyć wiele pozycji"
                defaultValue={defaultDataAsArray()}
                >
                {this.state.widgetData.map(option => {
                    return <option
                        key={option.value}
                        value={option.value}
                        children={option.label || option.value}
                        disabled={option?.disabled ? option.disabled : false} />;
                })}
            </select>
            <div className="forceHorizontalMiddle">
                <Switch id={switch_id} name={switch_id} onChange={(e) => changeSelechAll(e)} />
                <label htmlFor={switch_id}>Wybierz wszystkie</label>
            </div>
        </div>)
    }

    renderSingleSelect() {
        if(this.props.disabled) {
            return <span>{this.props.value}</span>
        }
        return <HTMLSelect options={this.state.widgetData} value={this.state.value ? this.state.value : this.props.value} disabled={this.props.disabled}
            onChange={(e) => {
                this.props.onValueChange(e.target.value)
                this.setState({value: e.target.value})
            }
            }/>
    }

    render() {
        if(this.state.widgetData === null || this.state.widgetData === undefined) {
            return <span><Spinner size={Spinner.SIZE_SMALL}/></span>;
        }
        if(this.props.definition.multiselect) {
            return this.renderMultiSelect();
        } else {
            return this.renderSingleSelect();
        }
    }

}

export default withAPI(DynamicSelect);
