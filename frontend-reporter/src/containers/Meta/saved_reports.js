import React, {useState} from "react";
import {withAPI} from "../../modules/api";
import {withRouter} from "react-router-dom";
import {MONTHS, WEEKDAYS_LONG, WEEKDAYS_SHORT} from "../Dialog/datetime";
import {DatePicker} from "@blueprintjs/datetime";
import {Button, ButtonGroup, Callout, Card, Spinner, Text} from "@blueprintjs/core";
import ReportView from "../Report/view";
import {saveBase64As} from "../../modules/fileSaver";
import Pagination from "../../components/pagination";

const formatDate = date => {
    const addZeros = val => {
        if (val < 10) {
            return "0" + val;
        }
        return val.toString();
    }
    return date.getFullYear() + '-' + addZeros(date.getMonth() + 1) + '-' + addZeros(date.getDate());
}

const showReport = (getREST, setOpenedResults, id) => {
    let api = getREST();
    api.get('meta/myReports/results/' + id).then(results => {
        setOpenedResults(results);
    }, reason => {
        alert(reason);
    });
}

const downloadReport = (getREST, button, id) => {
    let api = getREST();
    button.disabled = true;
    api.get('meta/myReports/download/' + id).then(results => {
        if (results.status === 'ok') {
            saveBase64As(results.content, results.content_type, results.filename);
        } else {
            alert(results.error);
        }
        button.disabled = false;
    }, reason => {
        alert(reason);
        button.disabled = false;
    });
}

const downloadReportFile = (getREST, button, id, fileIdx) => {
    let api = getREST();
    button.disabled = true;
    api.get('meta/myReports/downloadFile/' + id + '/' + fileIdx).then(results => {
        if (results.status === 'ok') {
            saveBase64As(results.content, results.content_type, results.filename);
        } else {
            alert(results.error);
        }
        button.disabled = false;
    }, reason => {
        alert(reason);
        button.disabled = false;
    });
}

const MetaSavedReportShow = ({openedResults, setOpenedResults}) => {
    return <div>
        <div style={{textAlign: 'right'}}><Button intent={"danger"}
                                                  onClick={() => setOpenedResults(null)}>Zamknij</Button></div>
        <ReportView results={openedResults.results} errors={openedResults.errors}/>
        <div style={{textAlign: 'right'}}><Button intent={"danger"}
                                                  onClick={() => setOpenedResults(null)}>Zamknij</Button></div>
    </div>;
}

const MetaSavedReportsList = ({getREST}) => {
    const [date, setDate] = useState(new Date());
    const [reports, setReports] = useState(null);
    const [openedResults, setOpenedResults] = useState(null);

    if (reports === null || reports.date !== formatDate(date)) {
        let api = getREST();
        api.get('meta/myReports/forDay/' + formatDate(date)).then(results => {
            setReports(results);
        }, reason => {
            alert(reason);
        });
    }

    if (openedResults !== null) {
        return <MetaSavedReportShow openedResults={openedResults} setOpenedResults={setOpenedResults}/>;
    }

    return (<div>
        <h1>Moje raporty</h1>
        <div style={{display: 'flex'}}>
            <DatePicker value={date} onChange={value => {
                setDate(value);
                setReports(null);
            }} canClearSelection={false}
                        highlightCurrentDay={true} dayPickerProps={{
                months: MONTHS,
                weekdaysLong: WEEKDAYS_LONG,
                weekdaysShort: WEEKDAYS_SHORT,
                firstDayOfWeek: 1,
                locale: 'pl',
                fixedWeeks: true,
            }}/>
            <Card style={{marginLeft: '5pt'}}>{(reports !== null ? <>
                {reports.reports.map(report => {
                    let plan = report.plan;
                    let intent = report.success ? null : "warning";
                    return (<Callout key={report.id} style={{marginBottom: '2pt'}} title={plan.name} intent={intent}>
                        {report.plan.report_title} <span className={"bp3-text-muted"}>{report.started_at}{report.finished_at === null ? ' (trwa)' : null}</span>
                        <div>
                            {report.success ?
                                <ButtonGroup>
                                    { report.results_info.can_open ? <Button intent={"success"}
                                            onClick={() => showReport(getREST, setOpenedResults, report.id)}>Otwórz</Button> : null }
                                    { report.results_info.can_download ? <Button intent={"success"}
                                            onClick={event => downloadReport(getREST, event.target, report.id)}>Pobierz</Button> : null }
                                    { report.results_info.result_files && report.results_info.result_files.length > 0 ? (report.results_info.result_files.map((filename, idx) => {
                                        return <Button intent={"success"}
                                                       onClick={event => downloadReportFile(getREST, event.target, report.id, idx)}>{filename}</Button>
                                    })) : null }
                                </ButtonGroup> :
                                <Text>
                                    <pre>{report.error_log}</pre>
                                </Text>}
                        </div>

                    </Callout>);
                })}
            </> : <Spinner/>)}</Card>
        </div>
    </div>);

}

const MetaSavedReportsSingle = ({getREST, jobId}) => {
    const [job, setJob] = useState(null);
    const [page, setPage] = useState(null);
    const [openedResults, setOpenedResults] = useState(null);


    const loadPage = newPage => {
        let api = getREST();
        api.get('meta/myReports/job/' + jobId + '/' + newPage).then(newJob => {
            setJob(newJob);
            setPage(newPage);
        }, reason => {
            alert(reason);
        });
    }

    if (job === null || job.id !== jobId) {
        loadPage(0);
        return <Spinner/>
    }

    if (openedResults !== null) {
        return <MetaSavedReportShow openedResults={openedResults} setOpenedResults={setOpenedResults}/>;
    }


    return (<div>
        <h1>{job.name}</h1>
        <h3>{job.report_title} <span className="bp3-text-muted"> | {job.schedule}</span></h3>
        {job.results.map(report => {
            let intent = report.success ? null : "warning";
            return (<Callout key={report.id} style={{marginBottom: '2pt'}} title={report.started_at + (report.finished_at === null ? ' (trwa)' : '')} intent={intent}>
                <div>
                    {report.success ?
                        <ButtonGroup>
                            { report.results_info.can_open ? <Button intent={"success"}
                                    onClick={() => showReport(getREST, setOpenedResults, report.id)}>Otwórz</Button> : null }
                            { report.results_info.can_download ? <Button intent={"success"}
                                    onClick={event => downloadReport(getREST, event.target, report.id)}>Pobierz</Button> : null }
                            { report.results_info.result_files && report.results_info.result_files.length > 0 ? (report.results_info.result_files.map((filename, idx) => {
                                return <Button intent={"success"}
                                               onClick={event => downloadReportFile(getREST, event.target, report.id, idx)}>{filename}</Button>
                            })) : null }
                        </ButtonGroup> :
                        <Text>
                            <pre>{report.error_log}</pre>
                        </Text>}
                </div>

            </Callout>);
        })}
        {job.page_count > 1 ?
            <Pagination totalCount={job.page_count} current={page + 1} onPaginate={page => loadPage(page - 1)}/> : null}
    </div>);

}


const MetaSavedReports = ({path, gui, getREST}) => {
    let urlParam = path.split(':')[1];
    if (urlParam === 'reports') {
        return <MetaSavedReportsList getREST={getREST}/>
    }
    return <MetaSavedReportsSingle getREST={getREST} jobId={parseInt(urlParam)}/>
}


export default withAPI(withRouter(MetaSavedReports));
