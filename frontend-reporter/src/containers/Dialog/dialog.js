import React from "react";
import "./dialog.css";
import {
    Text,
    Callout,
    Button, Popover, Position, Card, Icon
} from "@blueprintjs/core";
import "@blueprintjs/core/lib/css/blueprint.css";
import TabbedView from "./tabbedView";
import Field from "./field";
import CustomPanel from "./customPanel";
import {Form, Formik} from "formik";


/*
TODO ciekawostka: sprawdzanie czy element jeszcze jest zamontowany

 const isMounted = React.useRef<boolean>(false);


  React.useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
    };
  }, []);

if (!!isMounted.current) {
dispatch({ type: 'SUBMIT_SUCCESS' });
}

2.0.205.117 - adres serwera docelowego na raporty

 */

class Dialog extends React.Component {
    state = {
        // values: null,
    };

    static createProps(defn, parentProps) {
        let res = {'definition': defn};
        let ddefn = defn[2];
        if (ddefn.hasOwnProperty('path')) {
            res['path'] = ddefn['path'];
        } else {
            res['path'] = parentProps['path'];
        }
        if (ddefn.hasOwnProperty('ident') && res['path'].indexOf('/') === -1) {
            res['path'] += '/' + ddefn.ident;
        }
        return res;
    }

    constructor(props) {
        super(props);
        this.nextKey = 0;
        this.formRefs = {}
    }

    updateData() {
        // updateData wymagane
    }

    shouldComponentUpdate(nextProps, nextState, nextContext) {
        return !(nextProps.path === this.props.path && this.props.definition !== null);

    }

    getWidgetData(field, params) {
        return new Promise((resolve, reject) => {
            if (params === undefined) {
                params = null;
            }
            this.props.API_post('gui/dialog/' + this.props.path + '/' + field + '/data', params).then(resolve, reject);
        });
    }

    validate(values) {

    }

    getData() {
        let res = {};
        for (var fld in this.formRefs) {
            if (this.formRefs.hasOwnProperty(fld) && this.formRefs[fld].current !== null) {
                res[fld] = this.formRefs[fld].current.getValue();
            }
        }
        return res;
    }

    setValues(values) {
        for (var fld in this.formRefs) {
            if (values.hasOwnProperty(fld) && this.formRefs.hasOwnProperty(fld) && this.formRefs[fld].current !== null) {
                this.formRefs[fld].current.setValue(values[fld]);
            }
        }
    }

    bogusKey() {
        return this.nextKey++;
    }

    getInitialValues(elem) {
        let result = {};
        if (elem.hasOwnProperty('field')) {
            let value = null;
            if (elem.hasOwnProperty('default')) {
                value = elem.default;
            }
            result[elem.field] = value;
        }
        if (elem.hasOwnProperty('children')) {
            for (let i = 0; i < elem.children; i++) {
                let sub_res = this.getInitialValues(elem.children[i][1]);
                for (var k in sub_res) {
                    if (sub_res.hasOwnProperty(k)) {
                        result[k] = sub_res[k];
                    }
                }
            }
        }
        return result;
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
            return <Card style={{marginBottom: '5pt'}}>
                <Icon icon={"info-sign"} size={32} color={"#8888aa"} style={{float: 'left'}}/>
                <Text key={key} style={{ paddingLeft: '40px' }}>
                    {desc.text.split('\n').map((l, i) => <div key={i}>{l}</div>)}
                </Text>
            </Card>
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
        if (hierarchy.indexOf('CustomPanel') !== -1) {
            return <CustomPanel key={key} desc={desc} widget={widget}/>
        }
        if (widget === 'TabbedView') {
            let titles = [];
            let panels = [];
            let values = [];
            let defaultTab = 0;
            for (let i = 0; i < desc.children.length; i++) {
                let cld = desc.children[i][2]; // TODO XXX - pomyśleć o jakimś innym rozmontowywaniu tego opisu, niż po stałych indeksach
                if (cld.default) {
                    defaultTab = i;
                }
                titles.push(cld.title);
                values.push(cld.value);
                panels.push(this.buildFromDefinition(cld.children[0]));
            }
            let ref = null;
            if (desc.hasOwnProperty('field')) {
                ref = React.createRef();
                this.formRefs[desc.field] = ref;
            }
            return (
                <TabbedView key={key} titles={titles} panels={panels} defaultTab={defaultTab} vertical={desc.vertical}
                            field={desc.field} values={values} ref={ref}/>
            );
        }
        if (hierarchy.indexOf('Field') !== -1) {
            let ref = null;
            if (desc.hasOwnProperty('field')) {
                ref = React.createRef();
                this.formRefs[desc.field] = ref;
            }
            return (
                <Field fieldType={hierarchy} definition={desc} key={key} dialogProps={this.props}
                       onUpdate={(data) => this.updateData(data)} // TODO XXX to nie jest nigdzie robione
                       onWidgetDataNeed={params => this.getWidgetData(desc.field, params)} ref={ref}
                       defaultData={this.props.defaultData}/>
            )
        }
        return (
            <div key={key} style={{marginLeft: '10pt'}}>{widget}<br/>
                {(desc.children || []).map(cld => this.buildFromDefinition(cld))}
            </div>
        );
    }

    render() {
        let classess = 'dialog';
        let defn = this.props.definition;
        // let desc = defn[2];
        return (
            <div className={classess}>
                {this.buildFromDefinition(defn)}
            </div>
        );
    }

}


export default Dialog;
