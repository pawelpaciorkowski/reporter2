// import React from "react";
// import { ProgressBar, Callout, Switch } from "@blueprintjs/core";
// import { Table, VertTable, Info, ReportDiagram, Download, Action, Html } from "./widgets";
// import "./report.css";
// import { RepublikaEventStreamView } from "../Republika/republika";

// class ReportView extends React.Component {
//     constructor(props) {
//         super(props);
//         this.nextId = 0;
//     }

//     getKey() {
//         return this.nextId++;
//     }


//     resultWidget(desc) {
//         if (desc.type === 'table') {
//             return <Table desc={desc} key={this.getKey()} />;
//         }
//         if (desc.type === 'nested_table') {
//             return <Table desc={desc} key={this.getKey()} />;
//         }
//         if (desc.type === 'vertTable') {
//             return <VertTable desc={desc} key={this.getKey()} />;
//         }
//         if (desc.type === 'success') {
//             return <Info desc={desc} key={this.getKey()} type="success" />;
//         }
//         if (desc.type === 'info') {
//             return <Info desc={desc} key={this.getKey()} />;
//         }
//         if (desc.type === 'warning') {
//             return <Info desc={desc} key={this.getKey()} type="warning" />;
//         }
//         if (desc.type === 'error') {
//             return <Info desc={desc} key={this.getKey()} type="error" />;
//         }
//         if (desc.type === 'diagram') {
//             return <ReportDiagram desc={desc} key={this.getKey()} />;
//         }
//         if (desc.type === 'html') {
//             return <Html desc={desc} key={this.getKey()} />
//         }
//         if (desc.type === 'download') {
//             return <Download desc={desc} />
//         }
//         if (desc.type === 'action') {
//             return <Action desc={desc} onExecute={(token, callback) => this.props.onActionExecute(token, callback)} />
//         }
//         if (desc.type === 'republika') {
//             return (<div>
//                 {desc.title ? <h4 className="reportTabletitle">{desc.title}</h4> : null}
//                 <RepublikaEventStreamView eventStream={desc.data} />
//             </div>)
//         }
//         return <pre>{desc.type + '\n' + JSON.stringify(desc)}</pre>
//     }

//     render() {
//         if (this.props.content !== undefined) {
//             return (<div className="reportView oneShot">
//                 {this.props.content.map(result => this.resultWidget(result))}
//             </div>);
//         }
//         return (
//             <div className="reportView">
//                 {(!this.props.working || this.props.progress === 1) ? null :
//                     <div>
//                         {this.props.progress === null ? <ProgressBar animate={true} /> :
//                             <ProgressBar value={this.props.progress || null} animate={true} />}
//                         <div style={{ textAlign: 'right' }}>
//                             <Switch id="show_partial_results" style={{ display: "inline" }}
//                                 value={this.props.showPartialResults} onChange={e => this.props.setShowPartialResults(e.target.checked)} />
//                             <label htmlFor="show_partial_results">Pokaż wyniki częściowe</label>
//                         </div>
//                     </div>
//                 }
//                 {this.props.errors !== null && this.props.errors.length > 0 ? this.props.errors.map(error => (
//                     <Callout icon="error" intent="danger" key={error}>{error}</Callout>
//                 )) : null}
//                 {this.props.results !== null ? this.props.results.map(result => this.resultWidget(result)) : null}
//             </div>
//         )
//     }

// }

// export default ReportView;


import React from "react";
import { ProgressBar, Callout, Switch } from "@blueprintjs/core";
import { Table, VertTable, Info, ReportDiagram, Download, Action, Html } from "./widgets";
import "./report.css";
import { RepublikaEventStreamView } from "../Republika/republika";

function downloadBase64File(base64Data, fileName, contentType) {
    const linkSource = `data:${contentType};base64,${base64Data}`;
    const downloadLink = document.createElement('a');
    downloadLink.href = linkSource;
    downloadLink.download = fileName;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

class ReportView extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            selectedIds: new Set(),
        };
        this.nextId = 0;
    }

    componentDidUpdate(prevProps) {
        if (this.props.results !== prevProps.results && this.props.results !== null) {
            this.props.results.forEach(result => {
                if (result.type === 'base64file') {
                    downloadBase64File(result.content, result.filename, result.mimetype);
                }
                if (result.type === 'files' && Array.isArray(result.files)) {
                    result.files.forEach(file => {
                        if (file.type === 'base64file') {
                            downloadBase64File(file.content, file.filename, file.mimetype);
                        }
                    });
                }
            });

            // Czyścimy wyniki PO pobraniu
            if (this.props.clearResults) {
                this.props.clearResults();
            }
        }
    }

    getKey() {
        return this.nextId++;
    }

    toggleSelect(id) {
        this.setState(prevState => {
            const selected = new Set(prevState.selectedIds || []);
            if (selected.has(id)) {
                selected.delete(id);
            } else {
                selected.add(id);
            }
            return { selectedIds: selected };
        });
    }

    handleGeneratePDF() {
        const selectedIds = Array.from(this.state.selectedIds);
        console.log("Selected IDs before sending to backend: ", selectedIds);

        if (selectedIds.length === 0) {
            alert("Nie wybrano żadnych wyników do wygenerowania PDF!");
            return;
        }

        const selectedIdsString = selectedIds.join(',');

        const params = {
            ...this.props.currentParams,
            generate_pdf: 'tak',
            selected_ids: selectedIdsString,
        };

        console.log("Params being sent to backend: ", params);
        this.props.onGeneratePDF(params);
    }


    resultWidget(desc) {
        if (desc.type === 'table') {
            return <Table desc={desc} key={this.getKey()} />;
        }
        if (desc.type === 'nested_table') {
            return <Table desc={desc} key={this.getKey()} />;
        }
        if (desc.type === 'vertTable') {
            return <VertTable desc={desc} key={this.getKey()} />;
        }
        if (desc.type === 'success') {
            return <Info desc={desc} key={this.getKey()} type="success" />;
        }
        if (desc.type === 'info') {
            return <Info desc={desc} key={this.getKey()} />;
        }
        if (desc.type === 'warning') {
            return <Info desc={desc} key={this.getKey()} type="warning" />;
        }
        if (desc.type === 'error') {
            return <Info desc={desc} key={this.getKey()} type="error" />;
        }
        if (desc.type === 'diagram') {
            return <ReportDiagram desc={desc} key={this.getKey()} />;
        }
        if (desc.type === 'html') {
            return <Html desc={desc} key={this.getKey()} />;
        }
        if (desc.type === 'download') {
            return <Download desc={desc} key={this.getKey()} />;
        }
        if (desc.type === 'action') {
            return <Action desc={desc} onExecute={(token, callback) => this.props.onActionExecute(token, callback)} key={this.getKey()} />;
        }
        if (desc.type === 'republika') {
            return (
                <div key={this.getKey()}>
                    {desc.title ? <h4 className="reportTabletitle">{desc.title}</h4> : null}
                    <RepublikaEventStreamView eventStream={desc.data} />
                </div>
            );
        }
        return <pre key={this.getKey()}>{desc.type + '\n' + JSON.stringify(desc)}</pre>;
    }

    render() {
        if (this.props.content !== undefined) {
            return (
                <div className="reportView oneShot">
                    {this.props.content.map(result => this.resultWidget(result))}
                </div>
            );
        }

        const resultsWithoutBase64File = this.props.results
            ? this.props.results.filter(r => r.type !== 'base64file' && r.type !== 'files')
            : [];

        if (resultsWithoutBase64File.length === 0) {
            return (
                <div className="reportView">
                    {/* Możesz dodać np. komunikat o braku danych */}
                    <p style={{ textAlign: "center", marginTop: "20px", color: "#999" }}>
                        Brak wyników do wyświetlenia.
                    </p>
                </div>
            );
        }

        return (
            <div className="reportView">
                {(!this.props.working || this.props.progress === 1) ? null :
                    <div>
                        {this.props.progress === null
                            ? <ProgressBar animate={true} />
                            : <ProgressBar value={this.props.progress || null} animate={true} />}
                        <div style={{ textAlign: 'right' }}>
                            <Switch id="show_partial_results" style={{ display: "inline" }}
                                checked={this.props.showPartialResults}
                                onChange={e => this.props.setShowPartialResults(e.target.checked)} />
                            <label htmlFor="show_partial_results">Pokaż wyniki częściowe</label>
                        </div>
                    </div>
                }
                {this.props.errors !== null && this.props.errors.length > 0 ? this.props.errors.map(error => (
                    <Callout icon="error" intent="danger" key={error}>{error}</Callout>
                )) : null}
                {resultsWithoutBase64File.map(result => this.resultWidget(result))}
            </div>
        );
    }

}


export default ReportView;
