import React from "react";
import "./dialog.css";
import {
    Text,
    Callout,
    Button, Popover, Position
} from "@blueprintjs/core";
import "@blueprintjs/core/lib/css/blueprint.css";
import Field from "./field";
import FieldAccess from "./fieldAccess";
import {Form, Formik} from "formik";
import Dialog from "./dialog";


class RoleDialog extends Dialog {

    updateData(data) {
        const selected_access = this.props.select_data.uprawnienia.filter(u => u.id === data)[0]
        const role = selected_access.role;
        const labs = selected_access.labs;
        let labs_arr; //, role_arr;
        if (Array.isArray(labs)) {
            labs_arr = labs;
        } else {
            labs_arr = [labs];
        }

        // if (Array.isArray(role)) {
        //     role_arr = role;
        // } else {
        //     role_arr = [role];
        // }

        this.setState({
            selected_access:
            {
                id: data,
                role: role,
                labs: labs_arr,
            }
        })
        this.setAccessData(this.state)
        this.props.setAccess(this.state['selected_access'])
    }
    setAccessData(data) {
        this.props.setAccess(data)
    }

    buildFromDefinition(def) {
        let widget = def[0];
        let hierarchy = def[1];
        let desc = def[2];
        let key = this.bogusKey();
        if (widget === 'Dialog') {
            let initialValues = this.getInitialValues(desc);
            if (this.state.values === null) {
                // TODO XXX poniższe rzuca czerwony błąd - powinno się dziać gdzieś indzej
                // this.setState({values: initialValues});
                // wykomentowane i chyba działa
            }
            let formikParams = {
                initialValues: initialValues,
                onSubmit: (values, {setSubmitting}) => {
                    setSubmitting(true);
                    console.log('DIALOG onSubmit', values);
                    setSubmitting(false);
                },
            };
            let title = desc.title;
            if (desc.hasOwnProperty('help')) {
                title = (<span>{title} <Popover
                    content={<p style={{padding: '3pt', margin: 0}} dangerouslySetInnerHTML={{__html: desc.help}}/>}
                    position={Position.BOTTOM}>
                    <Button icon={"help"} title={"Pomoc"} minimal={true} small={true}/>
                </Popover></span>);
            }
            if(this.props.hasOwnProperty('data')) {
                setTimeout(() => this.setValues(this.props.data), 250);
            }
            return (
                <Callout key={key} title={title}>
                    <Formik {...formikParams}>
                        {({isSubmitting, setFieldValue, values}) => (<Form>
                            {desc.children.map(cld => this.buildFromDefinition(cld))}
                        </Form>)}
                    </Formik>
                </Callout>
            );
        }
        if (widget === 'HBox' || widget === 'VBox') {
            let classes = 'containerPrimitive container' + widget;
            if (desc.hasOwnProperty('align')) {
                classes += ' container_align_' + desc.align;
            }
            return (
                <div className={classes} key={key}>
                    {desc.children.map(cld => this.buildFromDefinition(cld))}
                </div>
            )
        }
        if (widget === 'InfoText') {
            return <Text key={key} className="bp3-text-muted">
                {desc.text.split('\n').map((l, i) => <div key={i}>{l}</div>)}
            </Text>
        }
        if (hierarchy.indexOf('Button') !== -1) {
            let onClick = () => {
                if (desc.preset !== undefined) {
                    this.setValues(desc.preset);
                }
            };
            if (desc.hasOwnProperty('action')) {
                onClick = () => {
                    this.props.onAction(desc.action, this.getData());
                };
            }
            return <Button key={key} text={desc.text} icon={desc.icon} intent={desc.intent} onClick={onClick}/>
        }
        // const validControls = ['RoleSelector','LabSelector', 
        //     "RaportSelector", "PosiadaneDostepySelector"]


        const validControls = ['LabSelector']
        const validControls2 = ['RoleSelector']
        const validControls3 = ['RaportSelector']
        // Posiadane dostępy
        if (hierarchy.indexOf('Field') !== -1 && hierarchy.indexOf('PosiadaneDostepySelector') !== -1) {
            let ref = null;
            if (desc.hasOwnProperty('field')) {
                ref = React.createRef();
                this.formRefs[desc.field] = ref;
            }
            return (
                <Field fieldType={hierarchy} definition={desc} key={key} dialogProps={this.props}
                    onUpdate={(data) => {
                        this.updateData(data)
                        this.props.setAccess(data)
                    }} // TODO XXX to nie jest nigdzie robione
                       onWidgetDataNeed={params => this.getWidgetData(desc.field, params)} ref={ref}
                       defaultData={this.props.defaultData}/>
            )
        }

        // Laboratoria
        if (hierarchy.indexOf('Field') !== -1 && hierarchy.some(h => validControls.includes(h))) {
            let ref = null;
            if (desc.hasOwnProperty('field')) {
                ref = React.createRef();
                this.formRefs[desc.field] = ref;
            }
            return (
                <FieldAccess fieldType={hierarchy} definition={desc} key={key} dialogProps={this.props}
                    selected_access={this.state.selected_access}
                    onWidgetDataNeed={params => this.getWidgetData(desc.field, params)} ref={ref}
                    defaultData={this.state.selected_access?.labs}
                    value={this.state.selected_access?.labs}/>
            )
        }

        // Role
        if (hierarchy.indexOf('Field') !== -1 && hierarchy.some(h => validControls2.includes(h))) {
            let ref = null;
            if (desc.hasOwnProperty('field')) {
                ref = React.createRef();
                this.formRefs[desc.field] = ref;
            }
            return (
                <FieldAccess fieldType={hierarchy} definition={desc} key={key} dialogProps={this.props}
                    selected_access={this.state.selected_access}
                    onWidgetDataNeed={params => this.getWidgetData(desc.field, params)} ref={ref}
                    defaultData={this.state.selected_access?.role}
                    value={this.state.selected_access?.role}/>
            )
        }

        // Report

        if (hierarchy.indexOf('Field') !== -1 && hierarchy.some(h => validControls3.includes(h))) {
            let ref = null;
            if (desc.hasOwnProperty('field')) {
                ref = React.createRef();
                this.formRefs[desc.field] = ref;
            }
            desc.multiselect = false;
            return (
                <FieldAccess fieldType={hierarchy} definition={desc} key={key} dialogProps={this.props}
                    selected_access={this.state.selected_access}
                    onWidgetDataNeed={params => this.getWidgetData(desc.field, params)} ref={ref}
                    defaultData={this.state.selected_access?.role}
                    value={this.state.selected_access?.role}/>
            )
        }
        // return (
        //     <div key={key} style={{marginLeft: '10pt'}}>{widget}<br/>
        //         {(desc.children || []).map(cld => this.buildFromDefinition(cld))}
        //     </div>
        // );
        return '';
    }


}


export default RoleDialog;
