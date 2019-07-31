using System;
using System.Collections.Generic;
using System.IdentityModel.Tokens.Jwt;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.JwtBearer;
// using Microsoft.AspNetCore.Authentication.OAuth;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.Extensions.Primitives;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;
using Newtonsoft.Json.Linq;
using ZMM.App.PyServicesClient;
using ZMM.App.ZSServiceClient;
using ZMM.Authorizations.Claims;
using ZMM.Helpers.ZMMDirectory;
//using Swashbuckle.AspNetCore.Swagger;
using System.IO;
using Microsoft.AspNetCore.SpaServices.AngularCli;
using Microsoft.OpenApi.Models;

namespace ZMM.App
{
    public class Startup
    {

        private readonly ILogger Logger;
        public IConfiguration Configuration { get; }
        public IHostingEnvironment Environment { get; }

        private string ContentDir = string.Empty;

        private const string XForwardedPathBase = "X-Forwarded-PathBase";
        private const string XForwardedProto = "X-Forwarded-Proto";

        public Startup(IConfiguration configuration, IHostingEnvironment environment,ILogger<Startup> logger)
        {
            Configuration = configuration;
            Environment = environment;
            Logger = logger;
            Logger.LogInformation("Initializing " + Configuration["Type"]);
            InitContentDir(ref ContentDir);
        }


        // This method gets called by the runtime. Use this method to add services to the container.
        public void ConfigureServices(IServiceCollection services)
        {
            #region MVC behaviour to specific .net version 2.2
            services.AddMvc().SetCompatibilityVersion(CompatibilityVersion.Version_2_2);
            #endregion


            #region Production profile works on Client UI /wwwroot with dotnet 2.2 inbuilt configuration
            string ClientUIDirectory = Configuration["WebApp:BuildPath"];
            if(ClientUIDirectory.Equals(string.Empty) || ClientUIDirectory == null) throw new Exception("Error : Please, configure WebApp:BuildPath in appsettings*.json");
            if(!System.IO.Directory.Exists(ClientUIDirectory)) throw new Exception("Error : It seems Client UI folder : " + ClientUIDirectory + " is not present; To resolve this, You need to publish solution once with command : dotnet publish ZMM.sln from ZMM folder.");
            services.AddSpaStaticFiles(configuration =>
            {
                configuration.RootPath =  ClientUIDirectory;
            });
            #endregion

            #region Identity Provider (KeyCloak) Integration
            services.AddAuthentication(options =>
            {
                options.DefaultAuthenticateScheme = CookieAuthenticationDefaults.AuthenticationScheme;
                options.DefaultSignInScheme = CookieAuthenticationDefaults.AuthenticationScheme;
                options.DefaultChallengeScheme = OpenIdConnectDefaults.AuthenticationScheme;
            })
            .AddCookie("Cookies")
            .AddOpenIdConnect(options =>
            {
                SetOIDCConfiguration(ref options, bool.Parse(Configuration["Authentication:OIDC:IsSecuredHTTP"]));
            });

            services.AddAuthorization(options =>
            {
                options.AddPolicy("Administrator", policy => policy.RequireClaim("role", "Administrator"));
                options.AddPolicy("User", policy => policy.RequireClaim("role", "User"));
                options.AddPolicy("CanUploadResourceInCode", policy => policy.RequireClaim("role", "User" , "Administrator"));
            });
            #endregion

            #region Add Swagger
            services.AddSwaggerGen(c =>
            {
                c.SwaggerDoc("v1", new OpenApiInfo { Title = "Zementis Modeler", Version = "v1" });
            });
            #endregion

            #region Initialize clients in singleton service
            var pySrvLocation = Configuration["PyServiceLocation:srvurl"];
            string ToolHostURL = Configuration["Tool:Host"];
            services.AddSingleton<IConfiguration>(Configuration);
            services.AddSingleton<IPyNNServiceClient>(new PyNNServiceClient(Configuration));
            services.AddSingleton<IPyAutoMLServiceClient>(new PyAutoMLServiceClient(Configuration));
            services.AddSingleton<IBaseImageForWielding>(new BaseImageForWielding(Configuration));
            services.AddSingleton<IPyJupyterServiceClient>(new PyJupyterServiceClient(ToolHostURL));
            services.AddSingleton<IPyZMEServiceClient>(new PyZMEServiceClient(Configuration));
            services.AddSingleton<IZSModelPredictionClient>(new ZSModelPredictionClient(Configuration));
            services.AddSingleton<IPyTensorServiceClient>(new PyTensorServiceClient(ToolHostURL,ContentDir));
            services.AddSingleton<IPyCompile>(new PyCompile(Configuration));
            #endregion
        }

        #region Setup User Identity Provider (KeyCloak) configuration
        public void SetOIDCConfiguration(ref OpenIdConnectOptions options, bool NeedSecuredHttp = true)
        {

                options.Authority = Configuration["Authentication:OIDC:AuthorizationEndpoint"];
                options.ClientId = Configuration["Authentication:OIDC:ClientId"];
                options.RequireHttpsMetadata = NeedSecuredHttp;
                options.SaveTokens = false;
                options.ClientSecret = Configuration["Authentication:OIDC:ClientSecret"];
                options.GetClaimsFromUserInfoEndpoint = true;
                options.SignedOutRedirectUri = Configuration["Authentication:OIDC:SignOutRedirectURL"];
                options.ResponseType = Configuration["Authentication:OIDC:ResponseType"];
                // options.ClaimActions.Add(new CustomClaimAction("role", "role", "user_roles", "User"));
                options.Events = new OpenIdConnectEvents
                {

                  	OnRedirectToIdentityProvider = redirectContext=>
                    {
                        if(NeedSecuredHttp) redirectContext.ProtocolMessage.RedirectUri = redirectContext.ProtocolMessage.RedirectUri.Replace("http://", "https://", StringComparison.OrdinalIgnoreCase);
                        return Task.FromResult(0);
                    },
                    OnRemoteFailure = context =>
                    {
                        context.HandleResponse();
                        context.Response.Redirect("/Account/Error?message=" + context.Failure.StackTrace);
                        return Task.FromResult(0);
                    }
                };
        }
        #endregion

        // This method gets called by the runtime. Use this method to configure the HTTP request pipeline.
        public void Configure(IApplicationBuilder app, IHostingEnvironment env, ILoggerFactory loggerFactory)
        {
            #region Enable HSTS option for production https enable system
            if(!env.IsEnvironment("Production")) app.UseHsts();
            #endregion

            #region Add Log Factory -> You can update its behaviour from appsettings*.json configuration
            AddLogger(ref loggerFactory);
            #endregion

          	app.Use((context, next) =>
            {
              	if (context.Request.Headers.TryGetValue(XForwardedPathBase, out StringValues pathBase))
                {
                    context.Request.PathBase = new PathString(pathBase);

                }
            	if(context.Request.Headers.TryGetValue(XForwardedProto, out StringValues proto))
                {
                	context.Request.Scheme = proto;
                }
              	return next();
            });

            // below is the fix for angular app reload redirections
            app.Use(async (context, next) =>
            {
                await next.Invoke();
                if (context.User.Identity.IsAuthenticated && context.Response.StatusCode == 404 && !context.Request.Path.Value.Contains("/api"))
                {

                    context.Request.Path = new PathString("/index.html");
                    await next.Invoke();
                }
                else
                {
                    context.Request.Path = new PathString("/");
                }
            });

            app.Use(async (context, next) =>
            {
                context.Features.Get<IHttpMaxRequestBodySizeFeature>()
                    .MaxRequestBodySize = 5368709120;

                var serverAddressesFeature = app.ServerFeatures.Get<Microsoft.AspNetCore.Hosting.Server.Features.IServerAddressesFeature>();
                var addresses = string.Join(", ", serverAddressesFeature?.Addresses);
                await next.Invoke();
            });

            app.UseExceptionHandler("/Account/Error");

            app.UseForwardedHeaders(new ForwardedHeadersOptions
            {
                ForwardedHeaders = ForwardedHeaders.XForwardedFor | ForwardedHeaders.XForwardedProto
            });

            app.UseStaticFiles();

            app.UseStaticFiles(new StaticFileOptions
            {
                FileProvider = new PhysicalFileProvider(ContentDir),
                RequestPath = "/data"
            });

            app.UseSwagger();
            app.UseSwaggerUI(c =>
            {
                c.SwaggerEndpoint("/swagger/v1/swagger.json", "ZMM API v1");
            });

            app.UseAuthentication();
            app.UseMvc(routes =>
            {
                routes.MapRoute(
                    name: "default",
                    template: "{controller}/{action}/{id?}");

                routes.MapRoute(
                    name: "train",
                    template: "{controller}/{action}");

                routes.MapSpaFallbackRoute(
                    name: "spa-fallback",
                    defaults: new { controller = "Home", action = "Index" });
            });

        }
        private void AddLogger(ref ILoggerFactory loggerFactory)
        {
            var LogFileName = "Logs" + System.IO.Path.DirectorySeparatorChar + "ZMM-{Date}-" + Guid.NewGuid().ToString() + ".log";
            loggerFactory.AddFile(LogFileName);
        }

        private void InitContentDir(ref string DirPath)
        {
            try
            {
                DirPath = Directory.GetCurrentDirectory();
                if(DirPath.Contains("src"))
                {
                    int startIdx = Directory.GetCurrentDirectory().IndexOf("src");
                    DirPath = Directory.GetCurrentDirectory().Substring(0, startIdx - 1);
                    DirPath = $"{Directory.GetParent(DirPath)}/ZMOD";
                }
                else
                {
                    DirPath = Directory.GetParent(DirPath).ToString() +"/ZMOD";
                }

                System.Console.WriteLine(Directory.GetCurrentDirectory());
                if (!Directory.Exists(DirPath))
                {
                    Directory.CreateDirectory(DirPath);
                }
                if (string.IsNullOrEmpty(DirectoryHelper.fileUploadDirectoryPath))
                {
                    DirectoryHelper.fileUploadDirectoryPath = DirPath.Replace(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                }
                DirectoryCreator.CreateFolders(DirPath);
                Logger.Log(LogLevel.Information, "Initialize content directory : " + DirPath);
            }
            catch(Exception ex)
            {
                Logger.LogCritical("Initializing ZMOD directory " + ex.StackTrace);
            }
        }
    }
}
