<?php

declare(strict_types=1);

namespace App\Controller;

use App\Entity\Company;
use App\Entity\Job;
use App\Entity\User;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Security\Http\Attribute\IsGranted;

#[Route('/company')]
#[IsGranted('ROLE_COMPANY')]
final class CompanyController extends AbstractController
{
    private function company(EntityManagerInterface $em): ?Company
    {
        $user = $this->getUser();
        if (!$user instanceof User) {
            throw $this->createAccessDeniedException();
        }

        return $em->getRepository(Company::class)->findOneBy(['owner' => $user]);
    }

    private function ownedJob(EntityManagerInterface $em, int $id): Job
    {
        $company = $this->company($em);
        if (!$company) {
            throw $this->createAccessDeniedException('No company profile for this account.');
        }

        $job = $em->getRepository(Job::class)->find($id);
        if (!$job || $job->getCompany()?->getId() !== $company->getId()) {
            throw $this->createNotFoundException('Job not found.');
        }

        return $job;
    }

    #[Route('/jobs', name: 'company_jobs')]
    public function jobs(EntityManagerInterface $em): Response
    {
        $company = $this->company($em);
        if (!$company) {
            $this->addFlash('danger', 'No company profile for this account. Log in as recruiter@jobboard.local.');

            return $this->redirectToRoute('app_home');
        }

        $jobs = $em->getRepository(Job::class)->findBy(
            ['company' => $company],
            ['createdAt' => 'DESC']
        );

        return $this->render('company/jobs.html.twig', [
            'jobs' => $jobs,
        ]);
    }

    #[Route('/jobs/new', name: 'company_job_new', methods: ['GET', 'POST'])]
    public function new(Request $request, EntityManagerInterface $em): Response
    {
        $company = $this->company($em);
        if (!$company) {
            $this->addFlash('danger', 'No company profile for this account. Log in as recruiter@jobboard.local.');

            return $this->redirectToRoute('app_home');
        }

        $job = (new Job())->setCompany($company);

        if ($request->isMethod('POST')) {
            if (!$this->isCsrfTokenValid('new-job', (string) $request->request->get('_token'))) {
                throw $this->createAccessDeniedException();
            }

            $this->applyJobForm($job, $request);
            $em->persist($job);
            $em->flush();
            $this->addFlash('success', 'Job created.');

            return $this->redirectToRoute('company_jobs');
        }

        return $this->render('company/new.html.twig', [
            'job' => $job,
        ]);
    }

    #[Route('/jobs/{id}/edit', name: 'company_job_edit', methods: ['GET', 'POST'], requirements: ['id' => '\d+'])]
    public function edit(int $id, Request $request, EntityManagerInterface $em): Response
    {
        $job = $this->ownedJob($em, $id);

        if ($request->isMethod('POST')) {
            if (!$this->isCsrfTokenValid('edit-job'.$job->getId(), (string) $request->request->get('_token'))) {
                throw $this->createAccessDeniedException();
            }

            $this->applyJobForm($job, $request);
            $em->flush();
            $this->addFlash('success', 'Job updated.');

            return $this->redirectToRoute('company_jobs');
        }

        return $this->render('company/edit.html.twig', [
            'job' => $job,
        ]);
    }

    #[Route('/jobs/{id}/delete', name: 'company_job_delete', methods: ['POST'], requirements: ['id' => '\d+'])]
    public function delete(int $id, Request $request, EntityManagerInterface $em): Response
    {
        $job = $this->ownedJob($em, $id);

        if (!$this->isCsrfTokenValid('delete-job'.$job->getId(), (string) $request->request->get('_token'))) {
            throw $this->createAccessDeniedException();
        }

        $em->remove($job);
        $em->flush();
        $this->addFlash('success', 'Job deleted.');

        return $this->redirectToRoute('company_jobs');
    }

    private function applyJobForm(Job $job, Request $request): void
    {
        $job
            ->setTitle((string) $request->request->get('title'))
            ->setDescription((string) $request->request->get('description'))
            ->setContractType((string) $request->request->get('contractType', 'CDI'))
            ->setLocation($request->request->get('location'))
            ->setRemote($request->request->getBoolean('remote'))
            ->setPublished($request->request->getBoolean('published'));
    }
}
