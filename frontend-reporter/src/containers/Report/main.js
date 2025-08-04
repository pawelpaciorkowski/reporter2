import React from "react";
import { withRouter } from "react-router-dom";
import { withAPI } from "../../modules/api";
import ReportControls from "./controls";
import ReportView from "./view";
import Dialog from "../Dialog/dialog";
import { Spinner } from "@blueprintjs/core";
import "./main.css";
import NewsAndDocs from "../NewsAndDocs/main";
import { saveBase64As } from "../../modules/fileSaver";

class ReportMain extends React.Component {
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
        // Cache dla paginacji
        cachedPages: new Map(),
        totalPages: 0,
        pageSize: 50,
        preloadProgress: 0
    };

    constructor(props) {
        super(props);
        this.launchDialogRef = React.createRef();

        // Dodaj funkcję obsługi checkboxów do window
        window.handleRowCheckbox = this.handleRowCheckbox.bind(this);
        window.selectAllCheckboxes = this.selectAllCheckboxes.bind(this);
        window.deselectAllCheckboxes = this.deselectAllCheckboxes.bind(this);
    }

    componentDidMount() {
        this.reloadIfNeeded();

        // Dodaj event listener do select generate_pdf
        setTimeout(() => {
            const generatePdfSelect = document.querySelector('select[name="generate_pdf"]');
            if (generatePdfSelect) {
                generatePdfSelect.addEventListener('change', () => this.updateSelectedIdsVisibility());
                this.updateSelectedIdsVisibility(); // Wywołaj początkowo
            }
        }, 1000);
    }

    componentDidUpdate(prevProps, prevState, snapshot) {
        this.reloadIfNeeded()
    }

    shouldComponentUpdate(nextProps, nextState, nextContext) {
        if (nextProps.path === this.props.path) {
            if (nextState.definition === null) {
                // return false; TODO: posprawdzać czy coś się popsuło
            }
        }
        return true;
    }

    handleRowCheckbox(checkbox) {
        const id = checkbox.getAttribute('data-id');
        const selectedIdsInput = document.querySelector('input[name="selected_ids"]');

        if (!selectedIdsInput) {
            console.error('Nie znaleziono pola selected_ids');
            return;
        }

        let currentIds = selectedIdsInput.value.trim();
        let idsArray = currentIds ? currentIds.split(',').map(id => id.trim()) : [];

        console.log('handleRowCheckbox - checkbox checked:', checkbox.checked);
        console.log('handleRowCheckbox - id:', id);
        console.log('handleRowCheckbox - currentIds:', currentIds);
        console.log('handleRowCheckbox - idsArray before:', idsArray);

        if (checkbox.checked) {
            if (!idsArray.includes(id)) {
                idsArray.push(id);
            }
        } else {
            idsArray = idsArray.filter(existingId => existingId !== id);
        }

        console.log('handleRowCheckbox - idsArray after:', idsArray);

        selectedIdsInput.value = idsArray.join(', ');
        console.log('handleRowCheckbox - selectedIdsInput.value after setting:', selectedIdsInput.value);
        console.log('handleRowCheckbox - selectedIdsInput.style.display:', selectedIdsInput.style.display);
        console.log('handleRowCheckbox - selectedIdsInput.closest(.field-container).style.display:', selectedIdsInput.closest('.field-container')?.style.display);

        const event = new Event('input', { bubbles: true });
        selectedIdsInput.dispatchEvent(event);

        const fieldTitle = selectedIdsInput.closest('.field-container')?.querySelector('.field-title');
        if (fieldTitle) {
            const baseTitle = "Wybrane ID rekordów (oddzielone przecinkami)";
            if (idsArray.length > 0) {
                fieldTitle.textContent = `${baseTitle} [${idsArray.length} zaznaczonych]`;
            } else {
                fieldTitle.textContent = baseTitle;
            }
        }
    }

    selectAllCheckboxes() {
        const checkboxes = document.querySelectorAll('.row-checkbox');
        const selectedIdsInput = document.querySelector('input[name="selected_ids"]');

        if (!selectedIdsInput) {
            console.error('Nie znaleziono pola selected_ids');
            return;
        }

        const ids = [];
        checkboxes.forEach(checkbox => {
            checkbox.checked = true;
            ids.push(checkbox.getAttribute('data-id'));
        });

        selectedIdsInput.value = ids.join(', ');
        const event = new Event('input', { bubbles: true });
        selectedIdsInput.dispatchEvent(event);

        const fieldTitle = selectedIdsInput.closest('.field-container')?.querySelector('.field-title');
        if (fieldTitle) {
            const baseTitle = "Wybrane ID rekordów (oddzielone przecinkami)";
            fieldTitle.textContent = ids.length > 0 ? `${baseTitle} [${ids.length} zaznaczonych]` : baseTitle;
        }
    }

    deselectAllCheckboxes() {
        const checkboxes = document.querySelectorAll('.row-checkbox');
        const selectedIdsInput = document.querySelector('input[name="selected_ids"]');

        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });

        if (selectedIdsInput) {
            selectedIdsInput.value = '';
            const event = new Event('input', { bubbles: true });
            selectedIdsInput.dispatchEvent(event);

            const fieldTitle = selectedIdsInput.closest('.field-container')?.querySelector('.field-title');
            if (fieldTitle) {
                fieldTitle.textContent = "Wybrane ID rekordów (oddzielone przecinkami)";
            }
        }
    }

    syncCheckboxesWithInput() {
        const selectedIdsInput = document.querySelector('input[name="selected_ids"]');
        if (!selectedIdsInput) return;

        const currentIds = selectedIdsInput.value.trim();
        if (!currentIds) return;

        const idsArray = currentIds.split(',').map(id => id.trim());
        const checkboxes = document.querySelectorAll('.row-checkbox');

        checkboxes.forEach(checkbox => {
            const id = checkbox.getAttribute('data-id');
            checkbox.checked = idsArray.includes(id);
        });
    }

    updateSelectedIdsVisibility() {
        const generatePdfSelect = document.querySelector('select[name="generate_pdf"]');
        const selectedIdsContainer = document.querySelector('input[name="selected_ids"]')?.closest('.field-container');

        console.log('updateSelectedIdsVisibility - generatePdfSelect:', generatePdfSelect);
        console.log('updateSelectedIdsVisibility - selectedIdsContainer:', selectedIdsContainer);

        if (generatePdfSelect && selectedIdsContainer) {
            const selectedValue = generatePdfSelect.value;
            console.log('updateSelectedIdsVisibility - selectedValue:', selectedValue);

            if (selectedValue === 'nie' || selectedValue === 'wszystkie') {
                selectedIdsContainer.style.opacity = '0.5';
                selectedIdsContainer.style.pointerEvents = 'none';
                console.log('updateSelectedIdsVisibility - deactivating field');
            } else {
                selectedIdsContainer.style.opacity = '1';
                selectedIdsContainer.style.pointerEvents = 'auto';
                console.log('updateSelectedIdsVisibility - activating field');
            }
        }
    }

    handlePageChange(newPage) {
        if (this.state.ident && this.state.cachedPages.has(newPage)) {
            // Pobierz dane z cache'a
            const cachedData = this.state.cachedPages.get(newPage);
            this.setState({
                result: cachedData,
                errors: cachedData.errors,
                currentPage: newPage
            });
        }
    }

    clearReportState() {
        console.log('🧹 Czyszczenie stanu aplikacji po pobraniu raportu');

        // Wyczyść stan po pobraniu raportu
        this.setState({
            result: null,
            errors: null,
            progress: 0,
            working: false,
            ident: null,
            params: null,
            cachedPages: new Map(),
            totalPages: 0,
            currentPage: 1,
            preloadProgress: 0
        });

        // Resetuj formularz do wartości początkowych
        setTimeout(() => {
            if (this.launchDialogRef.current && this.launchDialogRef.current.resetForm) {
                console.log('🔄 Wywołuję resetForm()');
                this.launchDialogRef.current.resetForm();
            } else {
                console.log('❌ launchDialogRef.current.resetForm nie istnieje');
                console.log('❌ launchDialogRef.current:', this.launchDialogRef.current);
            }
        }, 100);
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
                currentPage: 1,
            });
            let api = this.props.getREST();
            api.get('gui/page/' + path).then((resp) => {
                let newState = {};
                newState['definition'] = resp.dialog ? resp.dialog : false;
                if (resp.news) newState['news'] = resp.news;
                if (resp.docs) newState['docs'] = resp.docs;
                this.setState(newState);
            });
        }
    }

    launchReport(showResults) {
        let api = this.props.getREST();
        let url = 'report/start/' + this.state.path;
        let params = this.launchDialogRef.current.getData();

        console.log('launchReport - params before sending:', params);
        console.log('launchReport - selected_ids value:', params.selected_ids);

        // Jeśli wybrana jest opcja "zaznaczone", pobierz ID z zaznaczonych checkboxów
        if (params.generate_pdf === 'zaznaczone') {
            const checkboxes = document.querySelectorAll('.row-checkbox:checked');
            const selectedIds = Array.from(checkboxes).map(cb => cb.getAttribute('data-id'));
            params.selected_ids = selectedIds.join(', ');
            console.log('launchReport - auto-populated selected_ids:', params.selected_ids);
        }

        // Dodaj parametr fetch_all=true żeby pobrać wszystkie dane za jednym razem
        const paramsWithFetchAll = {
            ...params,
            fetch_all: true
        };

        this.setState({
            working: true,
            progress: 0.0,
            currentPage: 1,
            // Wyczyść cache przy nowym raporcie
            cachedPages: new Map(),
            totalPages: 0,
            preloadProgress: 0,
            // Wyczyść poprzednie wyniki
            result: null,
            errors: null
        });

        api.post(url, paramsWithFetchAll).then((resp) => {
            if (resp !== null) {
                if (resp.hasOwnProperty('ident')) {
                    this.setState({ ident: resp.ident, params: params });
                    setTimeout(() => this.monitorReport(showResults), 500);
                } else if (resp.hasOwnProperty('error')) {
                    api.toast('error', resp.error);
                    this.setState({ working: false });
                }
            }
        }, (reason) => {
            this.setState({ working: false });
        });
    }

    monitorReport(showResults, round = 0) {
        if (this.state.ident === null) {
            return;
        }

        let api = this.props.getREST();
        let url = `report/result/${this.state.path}/${this.state.ident}`;
        let queryParams = [];
        if (!showResults) queryParams.push('results=0');
        if (this.state.showPartialResults) queryParams.push('show_partial_results=1');
        if (queryParams.length > 0) url += '?' + queryParams.join('&');

        let nextCheck = (round > 10) ? 10000 : (round > 5) ? 2000 : 500;
        let errorNextCheck = 2000;

        api.get(url).then((resp) => {
            if (this.state.progress !== resp.progress || resp.progress === 1) {
                let newState = {
                    result: resp,
                    progress: resp.progress,
                    errors: resp.errors,
                    errorCnt: 0,
                };

                if (resp.progress === 1) {
                    newState.actions = resp.actions;
                    newState.working = false;

                    // Obsługa nowego formatu z fetch_all
                    if (resp.all_data && resp.pagination) {
                        // Wszystkie dane zostały pobrane za jednym razem
                        newState.totalPages = resp.pagination.total_pages;
                        newState.pageSize = resp.pagination.page_size;

                        // Utwórz cache ze wszystkich danych
                        const allData = resp.all_data;
                        const pageSize = resp.pagination.page_size;
                        const totalPages = resp.pagination.total_pages;

                        const newCachedPages = new Map();
                        for (let page = 1; page <= totalPages; page++) {
                            const startIdx = (page - 1) * pageSize;
                            const endIdx = startIdx + pageSize;
                            const pageData = allData.slice(startIdx, endIdx);

                            // Utwórz obiekt odpowiedzi dla każdej strony
                            const pageResponse = {
                                ...resp,
                                data: pageData,
                                pagination: {
                                    ...resp.pagination,
                                    current_page: page
                                }
                            };
                            newCachedPages.set(page, pageResponse);
                        }

                        newState.cachedPages = newCachedPages;
                        newState.preloadProgress = 100; // Wszystko załadowane

                        console.log(`✅ Wszystkie ${totalPages} stron załadowane do cache'a za jednym razem`);
                    } else if (resp.pagination) {
                        // Standardowa paginacja (fallback)
                        newState.cachedPages = new Map([[1, resp]]);
                        newState.totalPages = resp.pagination.total_pages;
                        newState.pageSize = resp.pagination.page_size;
                    }

                    this.setState(newState, () => {
                        setTimeout(() => this.syncCheckboxesWithInput(), 100);
                    });
                } else {
                    this.setState(newState);
                    setTimeout(() => this.monitorReport(showResults, round + 1), nextCheck);
                }
            } else {
                setTimeout(() => this.monitorReport(showResults, round + 1), nextCheck);
            }
        }, (reason) => {
            if (this.state.errorCnt < 3) {
                this.setState(prevState => ({ errorCnt: prevState.errorCnt + 1 }));
                setTimeout(() => this.monitorReport(showResults, round + 1), errorNextCheck + nextCheck);
            } else {
                this.setState({
                    errors: [reason],
                    progress: 1.0,
                    working: false,
                    errorCnt: 0,
                    // Wyczyść cache przy błędzie
                    cachedPages: new Map(),
                    totalPages: 0,
                    preloadProgress: 0
                });
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
            return (this.state.news || this.state.docs)
                ? <NewsAndDocs news={this.state.news} docs={this.state.docs} path={this.state.path} />
                : null;
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
                ) : (
                    <Dialog path={this.state.dialog_path} ref={this.launchDialogRef}
                        API_get={this.props.getREST().get}
                        API_post={this.props.getREST().post}
                        definition={this.state.definition} />
                )}

                <ReportControls path={this.state.path}
                    ident={this.state.ident} working={this.state.working}
                    actions={this.state.actions}
                    definition={this.state.definition[2]}
                    dialogRef={this.launchDialogRef}
                    onGenerateStart={(showResults) => this.launchReport(showResults)}
                    onClearState={() => this.clearReportState()} />
                <ReportView path={this.state.path}
                    params={this.state.params} ident={this.state.ident}
                    working={this.state.working}
                    progress={this.state.progress}
                    results={this.state.result ? (this.state.result.results || [this.state.result]) : null}
                    showPartialResults={this.state.showPartialResults}
                    setShowPartialResults={newVal => this.setState({ showPartialResults: newVal })}
                    onPageChange={this.handlePageChange.bind(this)}
                    onActionExecute={(token, callback) => {
                        console.log('DEBUG - onActionExecute called with token:', token);
                        const api = this.props.getREST();
                        const url = `report/action/${this.state.path}/${this.state.ident}/${token.type}/${token.index}`;
                        console.log('DEBUG - calling URL:', url);
                        api.get(url)
                            .then((resp) => {
                                console.log('DEBUG - action response:', resp);
                                if (callback) callback(resp);
                                if (resp.result && resp.result.type === 'base64file') {
                                    saveBase64As(resp.result.content, resp.result.mimetype, resp.result.filename);
                                    // Wyczyść stan po pobraniu raportu
                                    setTimeout(() => this.clearReportState(), 1000);
                                } else if (resp.result && resp.result.type === 'download') {
                                    // Wyczyść stan po pobraniu pliku
                                    setTimeout(() => this.clearReportState(), 1000);
                                }
                            })
                            .catch((error) => {
                                console.error('Action execution error:', error);
                                if (callback) callback(null);
                            });
                    }}
                    onClearState={() => this.clearReportState()}
                    errors={this.state.errors}
                    currentPage={this.state.currentPage}
                    cachedPages={this.state.cachedPages}
                    totalPages={this.state.totalPages}
                    preloadProgress={this.state.preloadProgress} />
            </div>
        );
    }
}

export default withAPI(withRouter(ReportMain));
