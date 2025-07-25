import React from "react";
import { ProgressBar, Callout, Switch } from "@blueprintjs/core";
import { Table, VertTable, Info, ReportDiagram, Download, Action, Html } from "./widgets";
import "./report.css";
import { RepublikaEventStreamView } from "../Republika/republika";

class ReportView extends React.Component {
    constructor(props) {
        super(props);
        this.nextId = 0;
    }

    getKey() {
        return this.nextId++;
    }


    resultWidget(desc) {
        console.log('ReportView.resultWidget called with:', desc);
        if (desc.type === 'table') {
            console.log('Rendering Table component with data length:', desc.data ? desc.data.length : 'no data');
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
            return <Html desc={desc} key={this.getKey()} />
        }
        if (desc.type === 'download') {
            return <Download desc={desc} />
        }
        if (desc.type === 'action') {
            return <Action desc={desc} onExecute={(token, callback) => this.props.onActionExecute(token, callback)} />
        }
        if (desc.type === 'republika') {
            return (<div>
                {desc.title ? <h4 className="reportTabletitle">{desc.title}</h4> : null}
                <RepublikaEventStreamView eventStream={desc.data} />
            </div>)
        }
        return <pre>{desc.type + '\n' + JSON.stringify(desc)}</pre>
    }

    render() {
        // Debug logs (can be removed later)
        console.log('ReportView render - results length:', this.props.results ? this.props.results.length : 'no results');

        if (this.props.content !== undefined) {
            console.log('Using content path with length:', this.props.content.length);
            return (<div className="reportView oneShot">
                {this.props.content.map(result => this.resultWidget(result))}
            </div>);
        }
        return (
            <div className="reportView">
                {(!this.props.working || this.props.progress === 1) ? null :
                    <div>
                        {this.props.progress === null ? <ProgressBar animate={true} /> :
                            <ProgressBar value={this.props.progress || null} animate={true} />}
                        <div style={{ textAlign: 'right' }}>
                            <Switch id="show_partial_results" style={{ display: "inline" }}
                                value={this.props.showPartialResults} onChange={e => this.props.setShowPartialResults(e.target.checked)} />
                            <label htmlFor="show_partial_results">Pokaż wyniki częściowe</label>
                        </div>
                    </div>
                }
                {this.props.errors && this.props.errors.length > 0 ? this.props.errors.map(error => (
                    <Callout icon="error" intent="danger" key={error}>{error}</Callout>
                )) : null}
                {this.props.results ? this.props.results.map(result => this.resultWidget(result)) : null}
            </div>
        )
    }

}

export default ReportView;
