import React from "react";
import { Callout, Button, Dialog } from "@blueprintjs/core";
import ReportDiagram from "./diagram";
import { saveBase64As } from "../../modules/fileSaver";
import Pagination from "../../components/pagination";


const Table = props => {
    // Sprawdź czy to jest raport archiwum wyników (używając flagi z backendu)
    const isArchiveReport = props.desc && props.desc.show_checkboxes === true;



    const renderHeaderCell = (cell, cellIndex) => {
        if (typeof cell !== "object") {
            cell = { title: cell, fontstyle: 'b' };
        }
        let attr = { style: {}, key: cellIndex };
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

    const renderHeaderRow = (row, rowIndex) => {
        return (<tr key={rowIndex}>
            {isArchiveReport && (
                <th style={{ width: '30px' }}>
                    <input
                        type="checkbox"
                        className="select-all-checkbox"
                        onChange={(e) => {
                            const checkboxes = document.querySelectorAll('.row-checkbox');
                            checkboxes.forEach(cb => cb.checked = e.target.checked);
                            // Wywołaj funkcję globalną
                            if (e.target.checked && window.selectAllCheckboxes) {
                                window.selectAllCheckboxes();
                            } else if (!e.target.checked && window.deselectAllCheckboxes) {
                                window.deselectAllCheckboxes();
                            }
                        }}
                    />
                </th>
            )}
            {row.map((cell, cellIndex) => renderHeaderCell(cell, cellIndex))}
        </tr>);
    };

    const renderHeader = hdr => {
        if (!hdr) {
            return null;
        }
        let header = null;
        if (Array.isArray(hdr[0])) {
            header = hdr.map((row, rowIndex) => renderHeaderRow(row, rowIndex));
        } else {
            header = renderHeaderRow(hdr, 0);
        }
        return <thead>{header}</thead>
    };

    const renderTableCell = (cell, cellIndex) => {
        if (cell === null || cell === undefined) {
            cell = '';
        }
        if (typeof cell !== "object") {
            cell = { value: cell };
        }
        let wrapper = value => value;
        let attr = { style: {}, key: cellIndex };
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
    const renderRow = (row, rowIndex) => {
        let rows = {};
        let rows_html = [];
        const resp = <tr key={rowIndex}>
            {isArchiveReport && (
                <td>
                    <input
                        type="checkbox"
                        className="row-checkbox"
                        data-id={row[0]} // ID jest w pierwszej kolumnie
                        onChange={(e) => {
                            // Wywołaj funkcję globalną
                            if (window.handleRowCheckbox) {
                                window.handleRowCheckbox(e.target);
                            }
                        }}
                    />
                </td>
            )}
            {row.map((cell, cellIndex) => {
                if (Array.isArray(cell)) {
                    let first;
                    for (let i in cell) {
                        if (i === "0") {
                            first = renderTableCell(cell[i], `${cellIndex}-0`);
                        } else {
                            const c = renderTableCell(cell[i], `${cellIndex}-${i}`)
                            if (!(i in rows)) {
                                rows[i] = []
                            }
                            rows[i].push(c)
                        }
                    }
                    return first;
                } else {
                    return renderTableCell(cell, cellIndex);
                }
            }
            )}
        </tr>
        for (let r in rows) {
            let row_cells = [];
            console.log(rows[r], rows, r)
            rows[r].map(td => row_cells.push(td))
            rows_html.push(<tr key={`sub-row-${r}`}>{row_cells}</tr>)
        }
        rows_html.unshift(resp)
        return rows_html
    };

    let desc = props.desc;
    let classes = "reportTable";

    // Obsługa paginacji
    const handlePageChange = (newPage) => {
        if (props.onPageChange) {
            props.onPageChange(newPage);
        }
    };

    return (<div>
        {desc.title ? <h4 className="reportTabletitle">{desc.title}</h4> : null}
        <table className={classes}>
            {renderHeader(desc.header)}
            <tbody>
                {desc.data.map((row, rowIndex) => renderRow(row, rowIndex))}
            </tbody>
        </table>

        {/* Paginacja */}
        {desc.pagination && (
            <div style={{ marginTop: '20px', textAlign: 'center' }}>
                <div style={{ marginBottom: '10px', fontSize: '14px', color: '#666' }}>
                    Strona {desc.pagination.current_page} z {desc.pagination.total_pages} |
                    Wyniki {(desc.pagination.current_page - 1) * desc.pagination.page_size + 1} -
                    {Math.min(desc.pagination.current_page * desc.pagination.page_size, desc.pagination.total_count)}
                    z {desc.pagination.total_count}
                    {props.cachedPages && (
                        <span style={{ marginLeft: '10px', color: '#28a745' }}>
                            (Cache: {props.cachedPages.size}/{props.totalPages} stron)
                            {props.preloadProgress === 100 && (
                                <span style={{ marginLeft: '5px', color: '#28a745' }}>
                                    ✅ Wszystkie dane załadowane
                                </span>
                            )}
                        </span>
                    )}
                </div>
                <Pagination
                    totalCount={desc.pagination.total_pages}
                    current={desc.pagination.current_page}
                    onPaginate={handlePageChange}
                />
            </div>
        )}
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
                    {desc.data.map(row => this.renderRow(row))}
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
        // Wyczyść stan po pobraniu pliku
        if (this.props.onClearState) {
            setTimeout(() => this.props.onClearState(), 1000);
        }
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