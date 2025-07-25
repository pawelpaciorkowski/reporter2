import React from "react";
import { Callout, Button, Dialog } from "@blueprintjs/core";
import ReportDiagram from "./diagram";
import { saveBase64As } from "../../modules/fileSaver";


const Table = props => {
    let nextKey = 0;
    let bogusKey = () => nextKey++;

    const renderHeaderCell = cell => {
        if (typeof cell !== "object") {
            cell = { title: cell, fontstyle: 'b' };
        }
        let attr = { style: {}, key: bogusKey() };
        if (cell.hasOwnProperty('colspan')) {
            attr.colSpan = cell.colspan;
        }
        if (cell.hasOwnProperty('rowspan')) {
            attr.rowSpan = cell.rowspan;
        }
        if (cell.hasOwnProperty('fontstyle')) {
            if (cell.fontstyle.indexOf('b') !== -1) {
                attr.style.fontWeight = 'bold';
            }
            if (cell.fontstyle.indexOf('u') !== -1) {
                attr.style.textDecoration = 'underline';
            }
            if (cell.fontstyle.indexOf('i') !== -1) {
                attr.style.fontStyle = 'italic';
            }
        }
        if (cell.hasOwnProperty('hint')) {
            attr.title = cell.hint;
        }
        if (cell.hasOwnProperty('dir')) {
            attr.style.textOrientation = 'mixed';
            if (cell.dir === 'tb') {
                attr.style.writingMode = 'vertical-rl';
            }
            if (cell.dir === 'bt') {
                attr.style.writingMode = 'sideways-lr';
                attr.style.minWidth = '2em';
                attr.style.verticalAlign = 'bottom';
            }
        }
        return <th {...attr}>{cell.title}</th>;
    };


    const renderHeaderRow = row => {
        return (<tr key={bogusKey()}>
            {row.map(cell => renderHeaderCell(cell))}
        </tr>);
    };

    const renderHeader = hdr => {
        if (!hdr) {
            return null;
        }
        let header = null;
        if (Array.isArray(hdr[0])) {
            header = hdr.map(row => renderHeaderRow(row));
        } else {
            header = renderHeaderRow(hdr);
        }
        return <thead>{header}</thead>
    };

    const renderTableCell = cell => {
        if (cell === null || cell === undefined) {
            cell = '';
        }
        if (typeof cell !== "object") {
            cell = { value: cell };
        }
        let wrapper = value => value;
        let attr = { style: {}, key: bogusKey() };
        if (cell.hasOwnProperty('fontstyle')) {
            if (cell.fontstyle.indexOf('b') !== -1) {
                attr.style.fontWeight = 'bold';
            }
            if (cell.fontstyle.indexOf('u') !== -1) {
                attr.style.textDecoration = 'underline';
            }
            if (cell.fontstyle.indexOf('i') !== -1) {
                attr.style.fontStyle = 'italic';
            }
            if (cell.fontstyle.indexOf('c') !== -1) {
                attr.style.textAlign = 'center';
            }
            if (cell.fontstyle.indexOf('r') !== -1) {
                attr.style.textAlign = 'right';
            }
            if (cell.fontstyle.indexOf('m') !== -1) {
                wrapper = value => <pre className="mono">{value}</pre>
            }
        }
        if (cell.hasOwnProperty('rowspan')) {
            attr.rowspan = cell.rowspan;
        }
        if (cell.hasOwnProperty('colspan')) {
            attr.colSpan = cell.colspan;
        }
        if (cell.hasOwnProperty('hint')) {
            attr.title = cell.hint;
        }
        if (cell.hasOwnProperty('color')) {
            attr.style.color = cell.color;
        }
        if (cell.hasOwnProperty('background')) {
            attr.style.background = cell.background;
        }
        if (cell.hasOwnProperty('html')) {
            return <td {...attr}>
                <div dangerouslySetInnerHTML={{ __html: cell.html }} />
            </td>
        }
        return <td {...attr}>{wrapper(cell.value)}</td>;
    };
    const renderRow = (row) => {
        let rows = {};
        let rows_html = [];
        const resp = <tr key={bogusKey()}>
            {row.map(cell => {
                if (Array.isArray(cell)) {
                    let first;
                    for (let i in cell) {
                        if (i === "0") {
                            first = renderTableCell(cell[i]);
                        } else {
                            const c = renderTableCell(cell[i])
                            if (!(i in rows)) {
                                rows[i] = []
                            }
                            rows[i].push(c)
                        }
                    }
                    return first;
                } else {
                    return renderTableCell(cell);
                }
            }
            )}
        </tr>
        for (let r in rows) {
            let row_cells = [];
            rows[r].map(td => row_cells.push(td))
            rows_html.push(<tr>{row_cells}</tr>)
        }
        rows_html.unshift(resp)
        return rows_html
    };

    let desc = props.desc;
    let classes = "reportTable";

    // Debug logging
    console.log('Table rendering with desc:', desc);
    console.log('Data exists:', !!desc.data);
    console.log('Data length:', desc.data ? desc.data.length : 'no data');

    return (<div>
        {desc.title ? <h4 className="reportTabletitle">{desc.title}</h4> : null}
        <table className={classes}>
            {renderHeader(desc.header)}
            <tbody>
                {desc.data && desc.data.map(row => renderRow(row))}
            </tbody>
        </table>
    </div>)
};

class VertTable extends React.Component {

    renderRowTitle(row) {
        return (<td className="rowTitle">{row.title}</td>);
    }

    renderRowValue(row) {
        if (row.value === null) {
            row.value = '[NULL]';
        }
        return (<td className="rowValue">{row.value.split('\n').map(line => <p
            style={{ margin: 0, padding: 0 }}>{line}</p>)}</td>);
    }

    renderRow(row) {
        return (<tr>
            {this.renderRowTitle(row)}
            {this.renderRowValue(row)}
        </tr>)
    }

    render() {
        let desc = this.props.desc;
        let classes = "reportTable vertical";
        return (<div>
            {desc.title ? <h4 className="reportTabletitle">{desc.title}</h4> : null}
            <table className={classes}>
                <tbody>
                    {desc.data && desc.data.map(row => this.renderRow(row))}
                </tbody>
            </table>
        </div>)
    }
}

class Info extends React.Component {
    render() {
        let icon = "info-sign";
        let intent = "primary";

        if (this.props.type === "success") {
            icon = "tick";
            intent = "success";
        }
        if (this.props.type === "warning") {
            icon = "warning-sign";
            intent = "warning";
        }
        if (this.props.type === "error") {
            icon = "error";
            intent = "danger";
        }
        return (<Callout icon={icon} intent={intent}>
            {this.props.desc.text}
        </Callout>)
    }
}

class Download extends React.Component {
    doDownload() {
        let desc = this.props.desc;
        saveBase64As(desc.content, desc.content_type, desc.filename);
    }

    render() {
        let nazwa = this.props.desc.title || this.props.desc.filename;
        return (
            <Callout intent="primary" icon={null}>
                <Button intent="success" icon="download"
                    onClick={() => this.doDownload()}>Pobierz plik {nazwa}</Button>
            </Callout>
        )
    }
}

class Action extends React.Component {
    state = {
        dialogContent: null,
        dialogOpen: false,
    };

    constructor(props) {
        super(props);
        this.dialog = React.createRef();
    }

    do() {
        let desc = this.props.desc;
        this.props.onExecute(desc.token, resp => {
            console.log('ACTION RESP', resp);
            if (desc.subtype === 'popup_view') {
                this.setState({
                    dialogContent: <pre>{resp}</pre>,
                    dialogOpen: true
                });
            }
        })
    }

    render() {
        let desc = this.props.desc;
        return (
            <div>
                <Button intent={desc.intent} icon={desc.icon}
                    onClick={() => this.do()}>{desc.title}</Button>
                <Dialog isOpen={this.state.dialogOpen} icon="info-sign" isCloseButtonShown={true} title="Podgląd"
                    usePortal={true} style={{ 'position': 'fixed', 'width': '100%', 'height': '100%' }}
                    onClose={() => this.setState({ dialogOpen: false })}>{this.state.dialogContent}</Dialog>
            </div>
        )
    }
}

class Html extends React.Component {
    render() {
        let desc = this.props.desc;
        return (<div className="">
            {desc.title ? <h4 className="htmltitle">{desc.title}</h4> : null}
            <div dangerouslySetInnerHTML={{ __html: desc.html }} />
        </div>);
    }
}

// TODO: dialog - różne tytuły, bardziej złożone interfejsy w środku

export { Table, VertTable, Info, ReportDiagram, Download, Action, Html };
