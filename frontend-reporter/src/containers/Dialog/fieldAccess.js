import React from "react";
import {InputGroup} from "formik-blueprint";
import {FormGroup, Radio, RadioGroup, Switch, HTMLSelect, TextArea} from "@blueprintjs/core";
import DynamicSelect from "./dynamicSelect";
import DynamicSearch from "./dynamicSearch";
import DateTime from "./datetime";
import Field from "./field";

const EMAIL_RE = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

class FieldAccess extends Field{
    /* TODO

        ten element zbiera wartości, wyświetla błędy, wyświetla podpisy pól itd

     */
    state = {
        error: null,
        value: null,
        selected_accesss: null
    };

    constructor(props) {
        super(props)
        this.setState({ selected_accesss: this.props.selected_accesss })
        this.setState({value: this.props.defaultData})
    }

    componentDidUpdate() {
    }

    getValue() {
        return this.state.value;
    }

    setValue(value) {
        // TODO: specjalne obsługiwanie niektórych pól, np kalendarzowych
        this.setState({value: value});
 
    }

    stdLabel() {
        let ft = this.props.fieldType;
        if (ft.indexOf('Switch') !== -1) {
            return false;
        }
        return true;
    }

    isHidden() {
        let def = this.props.definition;

        if(def.hasOwnProperty('hideInModes')) {
            if(this.props.dialogProps.mode && def.hideInModes.indexOf(this.props.dialogProps.mode) !== -1) {
                return true;
            }
        }
        return false;
    }

    renderFieldContents() {
        let def = this.props.definition;
        let ft = this.props.fieldType;
        let loadValue = this.props.definition.loadValue;
        let basicAttrs = {id: def.field, name: def.field, disabled: false};
        let inputProps = {style: {}};
        if(def.hasOwnProperty('disableInModes')) {
            if(this.props.dialogProps.mode && def.disableInModes.indexOf(this.props.dialogProps.mode) !== -1) {
                basicAttrs.disabled = true;
            }
        }
        if (ft.indexOf('Switch') !== -1) {
            let localHandleChange = (e) => {
                this.setState({value: e.target.checked});
            };
            return (<div className="forceHorizontal">
                <Switch checked={this.state.value || false} {...basicAttrs}
                        onChange={(e) => localHandleChange(e)}/>
                <label htmlFor={def.field}>{def.title}</label>
            </div>);
        }
        if (ft.indexOf('Radio') !== -1) {
            let options = [];
            for (var k in def.values) {
                if (def.values.hasOwnProperty(k)) {
                    options.push(<Radio key={k} value={k} label={def.values[k]}/>);
                }
            }
            return (<RadioGroup {...basicAttrs} // label={def.title}
                                onChange={(e) => this.handleChange(e)} selectedValue={this.state.value}>
                {options}
            </RadioGroup>)
        }
        if (ft.indexOf('Select') !== -1) {
            let items = [];
            for (k in def.values) {
                if (def.values.hasOwnProperty(k)) {
                    items.push({value: k, label: def.values[k]});
                }
            }
            return <HTMLSelect {...basicAttrs} options={items} value={this.state.value}
                               onChange={(e) => this.handleChange(e)}/>
        }
        if(def.hasOwnProperty('width')) {
            inputProps.style.width = def.width;
        }
        if (ft.indexOf('DynamicSelect') !== -1) {
            if (!loadValue) {
                return <DynamicSelect value={this.props.value} definition={this.props.definition}
                    inputProps={inputProps} {...basicAttrs}
                    onWidgetDataNeed={this.props.onWidgetDataNeed}
                    onValueChange={value => { this.setState({ value: value })}}
                    onChange={(e) => { this.handleChange(e) }}
                    defaultData={this.props.defaultData}/>;
            }

            return <DynamicSelect value={this.props.value} definition={this.props.definition}
                                  inputProps={inputProps} {...basicAttrs}
                                  onWidgetDataNeed={this.props.onWidgetDataNeed}
                                  onValueChange={value => this.setState({value: value})}
                                  onChange={(e) => this.handleChange(e)}/>;
        }
        if (ft.indexOf('DynamicSearch') !== -1) {
            return <DynamicSearch value={this.state.value} definition={this.props.definition}
                                  inputProps={inputProps} {...basicAttrs}
                                  onWidgetDataNeed={this.props.onWidgetDataNeed}
                                  onChange={(val) => this.handleValueChange(val)}/>;
        }
        if (ft.indexOf('DateTimeInput') !== -1) {
            let dateOnly = ft.indexOf('DateInput') !== -1;
            let timeOnly = ft.indexOf('TimeInput') !== -1;

            return <DateTime value={this.state.value} onChange={value => this.handleValueChange(value)}
                             canClearSelection={def.can_clear}
                             {...basicAttrs} dateOnly={dateOnly} timeOnly={timeOnly}/>
        }
        // Tu dokładamy atrybuty do podstawowego InputGroup w zależności od typu kontrolki
        let onChange = (e) => this.handleChange(e);
        if (ft.indexOf('EmailInput') !== -1) {
            let oldOnChange = onChange;
            onChange = (e) => {
                let badAddr = [];
                let value = e.target.value;
                value = value.replace(/#,;/g,' ');
                for(let addr of value.split(' ')) {
                    if(addr.length > 0 && !EMAIL_RE.test(addr)) {
                        badAddr.push(addr);
                    }
                }
                if(badAddr.length > 0) {
                    this.setState({error: 'Nieprawidłowy adres: ' + badAddr.join(', ')})
                } else {
                    this.setState({error: null});
                }
                return oldOnChange(e);
            }
        }
        if (def.textarea) {
            return <TextArea {...basicAttrs} onChange={onChange}
                               value={this.state.value || ''}/>;

        }
        return <InputGroup {...basicAttrs} onChange={onChange}
                           value={this.state.value || ''}/>;
    }

    renderField() {
        // let def = this.props.definition;
        // let ft = this.props.fieldType;
        // let fieldProps = {};

        // return (<FField {...fieldProps}>{this.renderFieldContents()}</FField>);
        return (<div>
            {this.renderFieldContents()}
            {this.state.error ? <div className={"formErrors"}>{this.state.error}</div> : null }
        </div>);
    }

    handleChange(event) {
        this.setState({value: event.target.value});
        return true;
    }

    handleValueChange(value) {
        this.setState({value: value});
        return true;
    }

    render() {
        let classNames = 'field';
        let def = this.props.definition;

        return this.isHidden()
            ? ''
            : this.stdLabel()
                ? <FormGroup  className={classNames} label={def.title}>{this.renderField()}</FormGroup>
                : this.renderField();
    }


}

export default FieldAccess;
