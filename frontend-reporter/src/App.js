import React from 'react';
import './App.css';
import {Router, Route} from "react-router-dom";
import {Provider} from "react-redux";
import {createBrowserHistory} from "history";
import {configureStore} from "./modules/utils.js";
import {APIProvider} from "./modules/api.js";
import TopBar from "./containers/TopBar/topBar";
import SideBar from "./containers/SideBar/sideBar";
import LoginPage from "./containers/LoginPage/LoginPage";
import ReportMain from "./containers/Report/main";
import MetaMain from "./containers/Meta/main";
import {KeyboardControlProvider} from "./modules/keyCtrl";
import {FocusStyleManager, Toaster} from "@blueprintjs/core";
import "@blueprintjs/core/lib/css/blueprint.css";
import "@blueprintjs/icons/lib/css/blueprint-icons.css";
import {RepublikaSampleView} from "./containers/Republika/sampleView";
import Start from "./containers/Start/main";

const history = createBrowserHistory();
const store = configureStore();

class App extends React.Component {

    state = {
        loginInfo: null,
    };

    constructor(props) {
        super(props);
        FocusStyleManager.onlyShowFocusOnTabs();
        this.toaster = React.createRef();
    }

    render = function () {

        return (
            <Provider store={store}>
                <Toaster ref={this.toaster}/>
                <APIProvider onLoginStateChange={(loginInfo) => {
                    this.setState({loginInfo: loginInfo});
                }} enableWebsocket={false} toaster={this.toaster}>
                    <KeyboardControlProvider>
                        <Router history={history}>
                            <div className="App" id="app">
                                <TopBar title="Reporter" loginInfo={this.state.loginInfo}/>
                                {this.state.loginInfo !== null ? <SideBar/> : null}
                                <div id="mainContent">
                                    <LoginPage loggedIn={this.state.loginInfo !== null}>
                                        <div id="content">
                                            <Route path="/" exact component={Start}/>
                                            <Route path="/raporty/:level1/" exact component={ReportMain}/>
                                            <Route path="/raporty/:level1/:level2/" exact component={ReportMain}/>
                                            <Route path="/raporty/:level1/:level2/:level3" exact
                                                   component={ReportMain}/>
                                            <Route path="/raporty/:level1/:level2/:level3/:level4" exact
                                                   component={ReportMain}/>
                                            <Route path="/meta/:level1/" exact component={MetaMain}/>
                                            <Route path="/meta/:level1/:level2/" exact component={MetaMain}/>
                                            <Route path="/meta/:level1/:level2/:level3" exact component={MetaMain}/>
                                            <Route path="/meta/:level1/:level2/:level3/:level4" exact component={MetaMain}/>
                                            <Route path="/test/" exact component={RepublikaSampleView} />
                                        </div>
                                    </LoginPage>
                                </div>
                            </div>
                        </Router>
                    </KeyboardControlProvider>
                </APIProvider>
            </Provider>
        );

    }
}


export default App;
