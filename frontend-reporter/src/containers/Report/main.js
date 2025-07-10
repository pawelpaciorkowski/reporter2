import React from "react";
import { withRouter } from "react-router-dom";
import { withAPI } from "../../modules/api";
import ReportControls from "./controls";
import ReportView from "./view";
import Dialog from "../Dialog/dialog";
import { Spinner } from "@blueprintjs/core";
import "./main.css";
import NewsAndDocs from "../NewsAndDocs/main";

class ReportMain extends React.Component {
    timeouts = [];
    state = {
        path: null,
        dialog_path: null,
        definition: null,
        params: null,
        result: null,
        ident: null,
        working: false,
        errors: null,
        actions: null,
        errorCnt: 0,
        showPartialResults: false,
        currentPage: 1,
        totalPages: 1,
        pageSize: 20, // Domyślny rozmiar strony
    };

    constructor(props) {
        super(props);
        this.launchDialogRef = React.createRef();
    }

    componentDidMount() {
        this.reloadIfNeeded();
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        this.reloadIfNeeded()
    }

    componentWillUnmount() {
        this.timeouts.forEach(clearTimeout);
    }

    shouldComponentUpdate(nextProps, nextState, nextContext) {
        if (nextProps.path === this.props.path) {
            if (nextState.definition === null) {
                // return false; TODO: posprawdzać czy coś się popsuło
            }
        }
        return true;
    }

    reloadIfNeeded() {
        let path = this.props.match.url.substr(1).replace(/\//g, '.');
        if (path !== this.state.path) {
            this.setState({
                path: path,
                dialog_path: path + '/LAUNCH',
                definition: null,
                params: null,
                result: null,
                ident: null,
                working: false,
                errors: null,
                actions: null,
                errorCnt: 0,
                docs: null,
                news: null,
            });
            let api = this.props.getREST();
            api.get('gui/page/' + path).then((resp) => {
                let newState = {}
                if (resp.dialog) {
                    newState['definition'] = resp.dialog;
                } else {
                    newState['definition'] = false;
                }
                if (resp.news) {
                    newState['news'] = resp.news;
                }
                if (resp.docs) {
                    newState['docs'] = resp.docs;
                }
                this.setState(newState);
            })
            // api.get('gui/dialog/' + dialog_path).then((resp) => {
            //     if (resp !== null) {
            //         this.setState({definition: resp});
            //     } else {
            //         this.setState({definition: false});
            //     }
            // }, reason => {
            //     this.setState({definition: false});
            // });
        }
    }

    launchReport(showResults, page = 1) {
        let api = this.props.getREST();
        let url = 'report/start/' + this.state.path;
        let params = this.launchDialogRef.current.getData();

        // Dodaj parametry paginacji
        params.page = page;
        params.pageSize = this.state.pageSize;

        this.setState((state) => {
            state.working = true;
            state.progress = 0.0;
            state.currentPage = page;
        });

        api.post(url, params).then((resp) => {
            if (resp !== null) {
                let newState = null;
                if (resp.hasOwnProperty('ident')) {
                    newState = {
                        ident: resp.ident,
                        params: params,
                    }
                } else if (resp.hasOwnProperty('error')) {
                    api.toast('error', resp.error);
                }
                if (newState !== null) {
                    this.setState(newState);
                }
                if (this.props.isWsAuthorized()) {
                    setTimeout(() => this.monitorReport(showResults), 500);
                } else {
                    setTimeout(() => this.monitorReport(showResults), 500);
                }
            }
        }, (reason) => {
            this.setState({ working: false })
        });
    }

    monitorReport(showResults, round) {
        console.log(`monitorReport: Called with showResults=${showResults}, round=${round}`);
        if (this.state.ident === null) {
            console.log("monitorReport: ident is null, returning.");
            return;
        }
        if (round === undefined) {
            round = 0;
        }
        let api = this.props.getREST();
        let url = 'report/result/' + this.state.path + '/' + this.state.ident;
        
        const queryParams = [];
        if (!showResults) {
            queryParams.push('results=0');
        } else if (this.state.showPartialResults) {
            queryParams.push('show_partial_results=1');
        }
        // Dodaj parametry paginacji do URL
        queryParams.push(`page=${this.state.currentPage}`);
        queryParams.push(`pageSize=${this.state.pageSize}`);

        if (queryParams.length > 0) {
            url += '?' + queryParams.join('&');
        }

        console.log(`monitorReport: Fetching URL: ${url}`);

        let nextCheck = 500;
        let errorNextCheck = 2000;
        if (round > 5) {
            nextCheck = 2000;
        }
        if (round > 10) {
            nextCheck = 10000;
        }

        api.get(url).then((resp) => {
            console.log("monitorReport: Received response:", resp);
            let newState = {
                progress: resp.progress,
                errors: resp.errors,
                errorCnt: 0,
            };

            let newResults = resp.results;
            let newTotalPages = this.state.totalPages;
            let newCurrentPage = this.state.currentPage;

            if (Array.isArray(resp.results)) {
                const paginationIndex = resp.results.findIndex(item => item.type === "pagination");
                if (paginationIndex !== -1) {
                    const paginationData = resp.results[paginationIndex];
                    newTotalPages = paginationData.total_pages;
                    newCurrentPage = paginationData.current_page;
                    newResults = resp.results.filter((_, index) => index !== paginationIndex);
                }
            }

            newState.result = { ...resp, results: newResults };
            newState.totalPages = newTotalPages;
            newState.currentPage = newCurrentPage;

            if (resp.progress === 1) {
                newState.actions = resp.actions;
                newState.working = false;
            } else {
                newState.actions = null;
                this.timeouts.push(setTimeout(() => this.monitorReport(showResults, round + 1), nextCheck));
            }
            this.setState(newState);
        }, (reason) => {
            console.error("monitorReport: API call failed:", reason);
            if (this.state.errorCnt < 3) {
                this.timeouts.push(setTimeout(() => this.monitorReport(showResults, round + 1), errorNextCheck + nextCheck));
                this.setState({ errorCnt: this.state.errorCnt + 1 });
            } else {
                this.setState({ errors: [reason], progress: 1.0, errorCnt: 0 });
            }
        });
    }

    onPaginate = (page) => {
        console.log(`onPaginate: Attempting to paginate to page ${page}`);
        this.setState({ currentPage: page }, () => {
            if (this.state.ident !== null) {
                console.log(`onPaginate: Report already running (ident: ${this.state.ident}), calling monitorReport.`);
                this.monitorReport(true);
            } else {
                console.log(`onPaginate: Report not running, calling launchReport.`);
                this.launchReport(true, page);
            }
        });
    }

    render() {
        if (!this.state.path) {
            return null;
        }
        if (this.state.definition === null) {
            return <Spinner />;
        }
        if (this.state.definition === false) {
            if (this.state.news || this.state.docs) {
                return <NewsAndDocs news={this.state.news} docs={this.state.docs} path={this.state.path} />
            } else {
                return null;
            }
        }
        return (
            <div id="reportMain">
                {this.state.news || this.state.docs ? (
                    <div className="dialogWithNews">
                        <Dialog path={this.state.dialog_path} ref={this.launchDialogRef}
                            API_get={this.props.getREST().get}
                            API_post={this.props.getREST().post}
                            definition={this.state.definition} />
                        <NewsAndDocs news={this.state.news} docs={this.state.docs} path={this.state.path} />
                    </div>
                ) : (<Dialog path={this.state.dialog_path} ref={this.launchDialogRef}
                    API_get={this.props.getREST().get}
                    API_post={this.props.getREST().post}
                    definition={this.state.definition} />)}

                <ReportControls path={this.state.path}
                    ident={this.state.ident} working={this.state.working}
                    actions={this.state.actions}
                    definition={this.state.definition[2]}
                    onGenerateStart={(showResults) => this.launchReport(showResults)}
                    selectedIds={this.state.selectedIds} />
                <ReportView path={this.state.path}
                    params={this.state.params} ident={this.state.ident}
                    working={this.state.working}
                    progress={this.state.progress}
                    results={this.state.result ? this.state.result.results : null}
                    showPartialResults={this.state.showPartialResults}
                    setShowPartialResults={newVal => {
                        this.setState({ showPartialResults: newVal })
                    }}
                    errors={this.state.errors}
                    currentPage={this.state.currentPage}
                    totalPages={this.state.totalPages}
                    onPaginate={this.onPaginate} />
            </div>
        );
    }


}

export default withAPI(withRouter(ReportMain));
