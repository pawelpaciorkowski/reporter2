import React from "react";
import './LoginPage.css'
import {withAPI} from "../../modules/api";
import {Field, Form, Formik} from "formik";
import {Button, Card, FormGroup} from "@blueprintjs/core";
import {InputGroup} from "formik-blueprint";
import {Link} from "react-router-dom";


class LoginPage extends React.Component {

    state = {
        lastError: null,
        tokenTried: false,
    };

    getTokenFromUrl = function() {
        if(window.location.href.indexOf('token=') !== -1) {
            let token = window.location.href.split('token=')[1];
            token = token.split('&')[0];
            return token;
        }
        return null;
    };


    getOauthCodeFromUrl = function() {
        if(window.location.href.indexOf('?code=') !== -1) {
            let code = window.location.href.split('code=')[1];
            code = code.split('&')[0];
            return code;
        }
        return null;
    };

    getErrorFromUrl = function () {
        if(window.location.href.indexOf('?error=') !== -1) {
            let error = window.location.href.split('error=')[1];
            error = error.split('&')[0];
            return error;
        }
        return null;
    }


    doLogin = function (login, passwd) {
        let api = this.props.getREST();
        api.login(login, passwd).then(result => {
            this.setState({lastError: null});
        }, reason => {
            this.setState({lastError: reason});
        });
    };

    tryLoginWithToken = function() {
        let api = this.props.getREST();
        let token = this.getTokenFromUrl();
        api.login('EXT$MOP', token).then(result => {
            window.location.href = window.location.href.split('token=')[0];
        }, reason => {
            this.setState({
                lastError: reason,
                tokenTried: true,
            });
        })
    };

    tryLoginWithOauthCode = function(code) {
        let api = this.props.getREST();
        let redirect_url = window.location.href.split('/').splice(0, 3).join('/') + '/';
        api.login('EXT$OAUTH', code + '^' + redirect_url).then(result => {
            window.location.href = window.location.href.split('code=')[0];
        }, reason => {
            alert(reason);
        })
    };

    doOauthLogin = function() {
        let api = this.props.getREST();
        let redirect_url = window.location.href.split('/').splice(0, 3).join('/') + '/';
        api.get('auth/oauth_login?redirect=' + redirect_url).then(resp => {
            window.location.href = resp.url;
        })
    };

    componentDidMount() {
        setTimeout(function () {
            if (window.location.href.indexOf('10.1.1.181') !== -1) {
                fetch('http://reporter.alab.lab/api/external/status').then(resp => {

                }, reason=>{
                    let res = prompt("Wykryto niepoprawną konfigurację DNS. W przyszłości mogą wystąpić problemy z dostępem do usług wewnętrznych Alab - skontaktuj się z serwisem IT (zgloszenia@alab.com.pl) z prośbą o prawidłową konfigurację DNS. Wpisz słowo rozumiem wielkimi literami, aby korzystać z aplikacji pod dotychczasowym adresem, w przeciwnym wypadku nastąpi próba przekierowania pod adres reporter.alab.lab.");
                    if(res !== 'ROZUMIEM') {
                        window.location.href = 'http://reporter.alab.lab/'
                    }
                })
            }
        }, 10);
    }

    render = function () {
        let error = this.getErrorFromUrl();
        if (this.props.loggedIn) {
            return this.props.children;
        } else {
            let token = this.getTokenFromUrl();
            if(token !== null && !this.state.tokenTried) {
                setTimeout(() => this.tryLoginWithToken(), 100);
                return <Card elevation={2} style={{ width: '400px', margin: 'auto', marginTop: '20pt', textAlign: 'center' }}>
                    Trwa logowanie
                </Card>;
            }
            let oauth_code = this.getOauthCodeFromUrl();
            if(oauth_code !== null) {
                setTimeout(() => this.tryLoginWithOauthCode(oauth_code), 10);
                return <Card elevation={2} style={{ width: '400px', margin: 'auto', marginTop: '20pt', textAlign: 'center' }}>
                    Trwa logowanie
                </Card>;
            }
            return (
                <Card elevation={2} style={{ width: '400px', margin: 'auto', marginTop: '20pt' }}>
                    {this.state.lastError ? <div className="errorMsg">{this.state.lastError}</div> : null}
                    {error ? <div className="errorMsg">{error}</div> : null}
                    <Formik onSubmit={(values, {setSubmitting}) => {
                        setSubmitting(true);
                        this.doLogin(values.login, values.passwd);
                        setSubmitting(false);
                    }} initialValues={{login: '', passwd: ''}}>
                        {({isSubmitting, setFieldValue, values}) => (
                            <Form>
                                <FormGroup
                                    label="Login">
                                    <Field name="login" id="login" component={InputGroup} autoFocus={true} large={true}/>
                                </FormGroup>
                                <FormGroup
                                    label="Hasło">
                                    <Field name="passwd" id="passwd" component={InputGroup} type="password" large={true}/>
                                </FormGroup>
                                {/*<Switch id="saveToken" name="saveToken" label="Zapamiętaj mnie na tym urządzeniu"/>*/}
                                <Button className="bp3-align-right" type="submit" disabled={isSubmitting}>Zaloguj</Button>

                                <span style={{float: "right", paddingTop: "4pt"}}><Link to="#" onClick={() => this.doOauthLogin()}>Zaloguj kontem Alab</Link></span>
                            </Form>
                        )}
                    </Formik>
                </Card>
            );
        }
    };

}


export default withAPI(LoginPage);
