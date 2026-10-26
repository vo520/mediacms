import uuid

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.test.utils import override_settings

from cms.version import VERSION
from files import views
from files.models import Page, TinyMCEMedia
from files.tests import create_account, create_media, fixture_path
from files.tests.media_utils import IMAGE


def factory_request(path, user=None):
    request = RequestFactory().get(path)
    request.user = user or AnonymousUser()
    request.session = SessionStore()
    request.LANGUAGE_CODE = "en"
    return request


class StaticPagesTest(TestCase):
    def test_about_shows_the_version_when_no_about_page_exists(self):
        response = self.client.get("/about")
        self.assertTemplateUsed(response, "cms/about.html")
        self.assertEqual(response.context["VERSION"], VERSION)
        self.assertContains(response, f"MediaCMS {VERSION}")

    def test_admin_written_about_page_replaces_the_default(self):
        Page.objects.create(slug="about", title="About our portal", description="<p>We host lectures</p>")
        response = self.client.get("/about")
        self.assertTemplateUsed(response, "cms/page.html")
        self.assertContains(response, "<h1>About our portal</h1>")
        self.assertContains(response, "<p>We host lectures</p>")

    def test_custom_page_is_served_by_its_slug(self):
        page = Page.objects.create(slug="faq", title="Frequent questions", description="Ask away")
        response = self.client.get(page.get_absolute_url())
        self.assertEqual(page.get_absolute_url(), "/faq")
        self.assertTemplateUsed(response, "cms/page.html")
        self.assertEqual(response.context["page"], page)
        self.assertContains(response, "Ask away")

    def test_unknown_slug_renders_the_not_found_template(self):
        response = self.client.get("/no-such-page")
        self.assertTemplateUsed(response, "404.html")
        self.assertNotIn("page", response.context)

    def test_simple_pages_render(self):
        pages = {"/tos": "cms/tos.html", "/setlanguage": "cms/set_language.html", "/contact": "cms/contact.html"}
        for url, template in pages.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)

    def test_setlanguage_page_posts_to_the_django_language_switcher(self):
        self.assertContains(self.client.get("/setlanguage"), 'action="/i18n/setlang/"')

    def test_switching_language_sets_the_language_cookie(self):
        response = self.client.post("/i18n/setlang/", {"language": "fr", "next": "/"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(response.cookies["django_language"].value, "fr")

    def test_robots_txt_points_at_the_sitemap(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertIn(b"Sitemap: http://testserver/sitemap.xml", response.content)

    def test_approval_required_page_renders(self):
        response = views.approval_required(factory_request("/approval_required/"))
        self.assertEqual(response.status_code, 200)


class SitemapTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_account()
        cls.public = create_media(cls.user, title="sitemap public")
        cls.private = create_media(cls.user, title="sitemap private", state="private")
        cls.unlisted = create_media(cls.user, title="sitemap unlisted", state="unlisted")
        cls.playlist = cls.user.playlists.create(title="sitemap playlist")
        cls.playlist.media.add(cls.public)

    def sitemap(self):
        return views.sitemap(factory_request("/sitemap.xml")).content.decode()

    def test_sitemap_is_xml_and_lists_the_static_pages(self):
        response = views.sitemap(factory_request("/sitemap.xml"))
        self.assertEqual(response["Content-Type"], "application/xml")
        content = response.content.decode()
        for path in ["/featured", "/latest", "/members", "/tags", "/categories", "/about", "/tos", "/contact"]:
            self.assertIn(f"<loc>http://testserver{path}</loc>", content)

    def test_sitemap_lists_only_listable_media(self):
        content = self.sitemap()
        self.assertIn(f"/view?m={self.public.friendly_token}", content)
        self.assertNotIn(self.private.friendly_token, content)
        self.assertNotIn(self.unlisted.friendly_token, content)

    def test_sitemap_lists_only_playlists_with_listable_media_and_visible_users(self):
        empty_playlist = self.user.playlists.create(title="empty sitemap playlist")
        content = self.sitemap()
        self.assertIn(f"/playlists/{self.playlist.friendly_token}</loc>", content)
        self.assertNotIn(f"/playlists/{empty_playlist.friendly_token}</loc>", content)
        self.assertIn(f"/user/{self.user.username}/</loc>", content)

    @override_settings(CAN_SEE_MEMBERS_PAGE="admins")
    def test_sitemap_hides_members_when_members_page_is_restricted(self):
        content = self.sitemap()
        self.assertNotIn("<loc>http://testserver/members</loc>", content)
        self.assertNotIn(f"/user/{self.user.username}/</loc>", content)


class UserProfilePagesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.profile = create_account()
        cls.other = create_account()
        cls.manager = create_account(is_manager=True)

    def get(self, path, user=None):
        if user:
            self.client.force_login(user)
        return self.client.get(path)

    def test_profile_pages_render_for_anyone(self):
        pages = {"": "cms/user.html", "/about": "cms/user_about.html", "/playlists": "cms/user_playlists.html"}
        for suffix, template in pages.items():
            with self.subTest(suffix=suffix):
                response = self.get(f"/user/{self.profile.username}{suffix}")
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.context["user"], self.profile)
                self.assertFalse(response.context["CAN_EDIT"])
                self.assertFalse(response.context["CAN_DELETE"])
                self.assertContains(response, f'profileId: "{self.profile.username}"')

    def test_owner_may_edit_but_not_delete_their_profile(self):
        response = self.get(f"/user/{self.profile.username}", self.profile)
        self.assertTrue(response.context["CAN_EDIT"])
        self.assertFalse(response.context["CAN_DELETE"])

    def test_manager_may_edit_and_delete_any_profile(self):
        response = self.get(f"/user/{self.profile.username}", self.manager)
        self.assertTrue(response.context["CAN_EDIT"])
        self.assertTrue(response.context["CAN_DELETE"])

    def test_unknown_user_redirects_to_members(self):
        for suffix in ["", "/about", "/playlists"]:
            with self.subTest(suffix=suffix):
                self.assertRedirects(self.get(f"/user/nobody-{uuid.uuid4().hex[:6]}{suffix}"), "/members", fetch_redirect_response=False)

    def test_shared_pages_are_private_to_their_owner(self):
        for suffix, template in [("/shared_with_me", "cms/user_shared_with_me.html"), ("/shared_by_me", "cms/user_shared_by_me.html")]:
            with self.subTest(suffix=suffix):
                self.client.logout()
                self.assertTemplateUsed(self.get(f"/user/{self.profile.username}{suffix}", self.profile), template)
                self.assertRedirects(self.get(f"/user/{self.profile.username}{suffix}", self.other), "/", fetch_redirect_response=False)


class TinyMCEUploadTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = create_account()
        cls.admin = create_account(is_superuser=True)

    def upload(self, user=None, with_file=True):
        if user:
            self.client.force_login(user)
        data = {}
        if with_file:
            with open(fixture_path(IMAGE), "rb") as fp:
                data["file"] = SimpleUploadedFile("pasted.png", fp.read(), content_type="image/png")
        return self.client.post("/tinymce/upload/", data)

    def test_only_superusers_may_upload_page_images(self):
        for user in [None, self.user]:
            with self.subTest(user=user and user.username):
                self.client.logout()
                response = self.upload(user)
                self.assertEqual(response.status_code, 403)
        self.assertFalse(TinyMCEMedia.objects.exists())

    def test_superuser_upload_is_stored_and_its_url_returned(self):
        response = self.upload(self.admin)
        self.assertEqual(response.status_code, 200)
        media = TinyMCEMedia.objects.get()
        self.assertEqual(response.json()["location"], media.url)
        self.assertEqual((media.original_filename, media.file_type, media.user), ("pasted.png", "image", self.admin))

    def test_upload_without_a_file_is_rejected(self):
        self.assertEqual(self.upload(self.admin, with_file=False).status_code, 400)

    def test_csrf_protection_is_enforced(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        with open(fixture_path(IMAGE), "rb") as fp:
            data = {"file": SimpleUploadedFile("pasted.png", fp.read(), content_type="image/png")}
        response = client.post("/tinymce/upload/", data)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(TinyMCEMedia.objects.exists())

    @override_settings(TINYMCE_UPLOAD_MAX_SIZE=10)
    def test_large_image_upload_is_rejected(self):
        self.client.force_login(self.admin)
        upload = SimpleUploadedFile("huge.png", b"x" * 11, content_type="image/png")
        response = self.client.post("/tinymce/upload/", {"file": upload})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Image file too large ( > 5mb )")
        self.assertFalse(TinyMCEMedia.objects.exists())

    def test_non_image_upload_is_rejected(self):
        self.client.force_login(self.admin)
        upload = SimpleUploadedFile("payload.png", b"not image", content_type="image/png")
        response = self.client.post("/tinymce/upload/", {"file": upload})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Invalid image type")
        self.assertFalse(TinyMCEMedia.objects.exists())


class AuthPagesLanguageSwitcherTest(TestCase):
    """The authentication pages ship an in-page language switcher."""

    def test_auth_pages_render_the_language_switcher(self):
        pages = ["/accounts/login/", "/accounts/login_system", "/accounts/signup/", "/accounts/password/reset/"]
        for url in pages:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="language-switcher"')
                self.assertContains(response, 'action="/i18n/setlang/"')
                self.assertContains(response, f'name="next" value="{url}"')

    def test_the_switcher_offers_the_configured_languages(self):
        response = self.client.get("/accounts/login/")
        self.assertContains(response, 'value="zh-hans"')
        self.assertContains(response, 'value="en"')

    def test_switching_language_from_an_auth_page_returns_to_it(self):
        response = self.client.post("/i18n/setlang/", {"language": "fr", "next": "/accounts/signup/"})
        self.assertRedirects(response, "/accounts/signup/", fetch_redirect_response=False)
        self.assertEqual(response.cookies["django_language"].value, "fr")


class AuthPagesTranslatedCopyTest(TestCase):
    """The sign in / sign up copy follows the active language."""

    def test_login_copy_is_translated(self):
        self.client.cookies["django_language"] = "zh-hans"
        response = self.client.get("/accounts/login_system")
        self.assertContains(response, "登录")
        self.assertContains(response, '<a href="/accounts/signup/">注册</a>')
        self.assertNotContains(response, "<h1>Sign In</h1>")

    def test_signup_copy_is_translated(self):
        self.client.cookies["django_language"] = "zh-hans"
        response = self.client.get("/accounts/signup/")
        self.assertContains(response, "注册")
        self.assertContains(response, '<a href="/accounts/login/">登录</a>')
        self.assertNotContains(response, "<h1>Sign Up</h1>")
